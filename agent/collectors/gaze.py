"""
Gaze / Screen-Attention Tracker
================================
Screen-gaze proxy combining two signals:

1. Mouse-cursor heuristics (always available on Linux)
2. Webcam-based gaze + blink estimation via MediaPipe FaceMesh
   (enabled when USE_WEBCAM_GAZE=true and mediapipe/opencv are installed)

Key fixes vs previous version:
  - Iris gaze uses relative displacement from the *neutral* iris centre
    (calibrated over first N frames) rather than raw normalised coords,
    which always mapped to "center".
  - Blink rate computed via Eye Aspect Ratio (EAR) on FaceMesh contour
    landmarks — now a real value instead of 0.
  - gaze_stability reflects actual iris jitter, not mouse movement,
    when webcam is active.

Output — GazeCollector.get_snapshot():
    {
        "gaze_zone":        str,    # "center"|"top"|"bottom"|"left"|"right"|"corner"
        "dwell_seconds":    float,  # seconds gaze has stayed in current zone
        "gaze_stability":   float,  # 0–1; 1 = rock-steady
        "reading_detected": bool,   # smooth left-to-right cursor drift
        "on_screen":        bool,
        "webcam_active":    bool,
        "blink_rate":       float,  # blinks per minute (rolling 60 s window)
    }
"""

import math
import os
import threading
import time
from collections import deque

# ── optional dependencies ─────────────────────────────────────────────────────

try:
    import Xlib.display  # type: ignore
    _XLIB_OK = True
except ImportError:
    _XLIB_OK = False

cv2 = None
mp  = None
_MEDIAPIPE_OK = False
try:
    import cv2 as _cv2      # type: ignore
    import mediapipe as _mp  # type: ignore
    _ = _mp.solutions.face_mesh   # raises AttributeError on mediapipe >= 0.10.15
    cv2 = _cv2
    mp  = _mp
    _MEDIAPIPE_OK = True
except (ImportError, AttributeError):
    pass

# ── constants ─────────────────────────────────────────────────────────────────

DWELL_THRESHOLD  = 1.5    # s before a position counts as "dwelling"
STABILITY_WINDOW = 2.0    # s of history used for stability
READING_MIN_RUN  = 3      # minimum rightward steps for reading detection
ZONE_MARGIN      = 0.25   # fractional border for edge zones

USE_WEBCAM_GAZE  = os.getenv("USE_WEBCAM_GAZE", "true").lower() == "true"
WEBCAM_INDEX     = int(os.getenv("WEBCAM_INDEX", "0"))
WEBCAM_FPS_CAP   = 10     # frames/sec to process

# Calibration: number of frames to collect neutral iris position on startup
CALIBRATION_FRAMES = 30

# Gaze sensitivity: how far iris must move from neutral (in normalised units)
# before we assign a non-center zone.  Tune lower to make it more sensitive.
GAZE_THRESHOLD_X = 0.018
GAZE_THRESHOLD_Y = 0.014

# Eye Aspect Ratio threshold — below this value we count a blink
EAR_THRESHOLD    = 0.25
# Minimum frames eye must stay below EAR_THRESHOLD to count as one blink
EAR_CONSEC_MIN   = 2
# Rolling window for blink rate (seconds)
BLINK_WINDOW     = 60.0

# FaceMesh landmark indices
_LEFT_IRIS   = [468, 469, 470, 471]
_RIGHT_IRIS  = [473, 474, 475, 476]
# EAR landmarks: [p1(corner), p2(top-outer), p3(top-inner),
#                 p4(corner), p5(bot-inner), p6(bot-outer)]
_LEFT_EYE_EAR  = [362, 385, 387, 263, 373, 380]
_RIGHT_EYE_EAR = [33,  160, 158, 133, 153, 144]


# ── helpers ───────────────────────────────────────────────────────────────────

def _zone_from_delta(dx: float, dy: float) -> str:
    """
    Map iris displacement from neutral to a zone label.
    dx/dy are normalised differences (current - neutral).
    """
    tx, ty = GAZE_THRESHOLD_X, GAZE_THRESHOLD_Y
    beyond_x = abs(dx) > tx
    beyond_y = abs(dy) > ty

    if not beyond_x and not beyond_y:
        return "center"
    if beyond_x and beyond_y:
        return "corner"
    if beyond_y:
        return "top" if dy < 0 else "bottom"
    return "left" if dx < 0 else "right"


def _cursor_zone(nx: float, ny: float) -> str:
    """Map normalised (0–1) cursor coords to a zone label."""
    m    = ZONE_MARGIN
    in_x = m < nx < 1 - m
    in_y = m < ny < 1 - m
    if in_x and in_y:
        return "center"
    if not in_x and not in_y:
        return "corner"
    if not in_y:
        return "top" if ny <= m else "bottom"
    return "left" if nx <= m else "right"


def _ear(lm, indices: list) -> float:
    """Eye Aspect Ratio from six FaceMesh landmark indices."""
    p = [lm[i] for i in indices]
    def d(a, b):
        return math.hypot(a.x - b.x, a.y - b.y)
    return (d(p[1], p[5]) + d(p[2], p[4])) / (2.0 * d(p[0], p[3]) + 1e-6)


# ── webcam thread ─────────────────────────────────────────────────────────────

class _WebcamGaze:
    """
    Background thread: reads webcam, tracks iris gaze zone, detects blinks.

    Calibration phase (first CALIBRATION_FRAMES frames with a detected face):
      - Collects iris nx/ny values and averages them as the "neutral" position.
      - During calibration, zone is reported as "center".

    Post-calibration:
      - Zone derived from iris displacement relative to neutral.
      - Blinks detected via EAR; rate computed over rolling BLINK_WINDOW.
    """

    def __init__(self) -> None:
        self.zone       = "center"
        self.active     = False
        self.stability  = 1.0
        self.blink_rate = 0.0

        self._lock  = threading.Lock()
        self._stop  = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True,
                                        name="WebcamGaze")
        self._thread.start()

    # ------------------------------------------------------------------
    def _run(self) -> None:
        if mp is None or cv2 is None:
            return

        cap = cv2.VideoCapture(WEBCAM_INDEX)
        if not cap.isOpened():
            print("[GazeCollector] Webcam could not be opened — "
                  "falling back to cursor-proxy mode.")
            return

        interval = 1.0 / WEBCAM_FPS_CAP

        # Calibration state
        cal_samples: list[tuple[float, float]] = []
        neutral_nx: float | None = None
        neutral_ny: float | None = None

        # Iris history for stability (raw nx values)
        iris_history: deque[float] = deque(maxlen=int(STABILITY_WINDOW * WEBCAM_FPS_CAP))

        # Blink state
        ear_below_count = 0
        in_blink        = False
        blink_times: deque[float] = deque()   # timestamps of confirmed blinks

        try:
            with mp.solutions.face_mesh.FaceMesh(
                max_num_faces=1,
                refine_landmarks=True,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5,
            ) as face_mesh:

                while not self._stop.is_set():
                    t0    = time.monotonic()
                    ok, frame = cap.read()

                    if not ok:
                        time.sleep(interval)
                        continue

                    result = face_mesh.process(
                        cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    )

                    if not result.multi_face_landmarks:
                        with self._lock:
                            self.active = False
                        elapsed = time.monotonic() - t0
                        time.sleep(max(0.0, interval - elapsed))
                        continue

                    lm   = result.multi_face_landmarks[0].landmark
                    npts = len(lm)
                    now  = time.monotonic()

                    # ── iris position ──────────────────────────────────
                    xs = [lm[i].x for i in _LEFT_IRIS + _RIGHT_IRIS if i < npts]
                    ys = [lm[i].y for i in _LEFT_IRIS + _RIGHT_IRIS if i < npts]

                    if not xs:
                        elapsed = time.monotonic() - t0
                        time.sleep(max(0.0, interval - elapsed))
                        continue

                    nx = sum(xs) / len(xs)
                    ny = sum(ys) / len(ys)

                    # ── calibration ────────────────────────────────────
                    if neutral_nx is None:
                        cal_samples.append((nx, ny))
                        if len(cal_samples) >= CALIBRATION_FRAMES:
                            neutral_nx = sum(s[0] for s in cal_samples) / len(cal_samples)
                            neutral_ny = sum(s[1] for s in cal_samples) / len(cal_samples)
                            print(f"[GazeCollector] Calibrated neutral iris: "
                                  f"nx={neutral_nx:.4f} ny={neutral_ny:.4f}")
                        zone = "center"
                    else:
                        dx   = nx - neutral_nx
                        dy   = ny - neutral_ny
                        zone = _zone_from_delta(dx, dy)

                    # ── stability (iris jitter) ─────────────────────────
                    iris_history.append(nx)
                    if len(iris_history) >= 2:
                        pts   = list(iris_history)
                        jitter = sum(abs(pts[i] - pts[i-1])
                                     for i in range(1, len(pts)))
                        # 0.05 normalised units/frame = totally unstable
                        max_jitter = 0.05 * len(pts)
                        stab = round(max(0.0, 1.0 - jitter / max_jitter), 3)
                    else:
                        stab = 1.0

                    # ── blink detection via EAR ────────────────────────
                    l_ear   = _ear(lm, _LEFT_EYE_EAR)
                    r_ear   = _ear(lm, _RIGHT_EYE_EAR)
                    avg_ear = (l_ear + r_ear) / 2.0

                    if avg_ear < EAR_THRESHOLD:
                        # Eye is closing / closed
                        ear_below_count += 1
                        in_blink = True
                    else:
                        # Eye has re-opened — if we were in a blink long
                        # enough, count it
                        if in_blink and ear_below_count >= EAR_CONSEC_MIN:
                            blink_times.append(now)
                        in_blink        = False
                        ear_below_count = 0

                    # Prune blink timestamps outside rolling window
                    cutoff = now - BLINK_WINDOW
                    while blink_times and blink_times[0] < cutoff:
                        blink_times.popleft()

                    # blinks per minute
                    bpm = len(blink_times) * (60.0 / BLINK_WINDOW)

                    with self._lock:
                        self.zone       = zone
                        self.active     = True
                        self.stability  = stab
                        self.blink_rate = round(bpm, 2)

                    elapsed = time.monotonic() - t0
                    time.sleep(max(0.0, interval - elapsed))

        finally:
            cap.release()

    # ------------------------------------------------------------------
    def get(self) -> tuple[str, bool, float, float]:
        """Return (zone, active, stability, blink_rate)."""
        with self._lock:
            return self.zone, self.active, self.stability, self.blink_rate

    def stop(self) -> None:
        self._stop.set()


# ── main collector ────────────────────────────────────────────────────────────

class GazeCollector:
    """
    Thread-safe screen-gaze proxy.

    Usage::

        gc = GazeCollector()
        gc.start()
        ...
        snap = gc.get_snapshot()
        gc.stop()
    """

    def __init__(self) -> None:
        self._lock        = threading.Lock()
        self._running     = False
        self._thread: threading.Thread | None = None
        self._webcam_gaze: _WebcamGaze | None = None

        # Shared state (written by _run, read by get_snapshot)
        self._zone       = "center"
        self._dwell_secs = 0.0
        self._stability  = 1.0
        self._reading    = False
        self._on_screen  = True
        self._blink_rate = 0.0

        # Cursor history — only the background thread touches this
        self._history: deque[tuple[float, int, int]] = deque()

        self._sw, self._sh = self._get_screen_size()

    # ── screen geometry ───────────────────────────────────────────────────────

    @staticmethod
    def _get_screen_size() -> tuple[int, int]:
        if _XLIB_OK:
            try:
                d  = Xlib.display.Display()
                sc = d.screen()
                return sc.width_in_pixels, sc.height_in_pixels
            except Exception:
                pass
        return 1920, 1080

    # ── cursor ────────────────────────────────────────────────────────────────

    @staticmethod
    def _get_cursor() -> tuple[int, int] | None:
        if not _XLIB_OK:
            return None
        try:
            d   = Xlib.display.Display()
            dat = d.screen().root.query_pointer()
            return dat.root_x, dat.root_y
        except Exception:
            return None

    # ── cursor-based stability ────────────────────────────────────────────────

    def _cursor_stability(self) -> float:
        pts = list(self._history)
        if len(pts) < 2:
            return 1.0
        total = sum(
            math.hypot(pts[i][1] - pts[i-1][1], pts[i][2] - pts[i-1][2])
            for i in range(1, len(pts))
        )
        max_expected = 1_000.0 * STABILITY_WINDOW
        return round(max(0.0, 1.0 - total / max_expected), 3)

    # ── background loop ───────────────────────────────────────────────────────

    def _run(self) -> None:
        prev_zone     = "center"
        dwell_start   = time.monotonic()
        rightward_run = 0
        last_x: int | None = None

        while self._running:
            now = time.monotonic()
            pos = self._get_cursor()

            if pos is None:
                time.sleep(0.25)
                continue

            cx, cy = pos
            nx = cx / self._sw if self._sw > 0 else 0.5
            ny = cy / self._sh if self._sh > 0 else 0.5
            on_screen = 0 <= cx <= self._sw and 0 <= cy <= self._sh

            # Webcam overrides zone + stability + blink_rate when active
            blink_rate = 0.0
            if self._webcam_gaze is not None:
                wc_zone, wc_active, wc_stab, wc_bpm = self._webcam_gaze.get()
                if wc_active:
                    zone       = wc_zone
                    stability  = wc_stab
                    blink_rate = wc_bpm
                else:
                    zone      = _cursor_zone(nx, ny)
                    stability = self._cursor_stability()
            else:
                zone      = _cursor_zone(nx, ny)
                stability = self._cursor_stability()

            # Dwell
            if zone != prev_zone:
                dwell_start = now
                prev_zone   = zone
            dwell_secs = now - dwell_start

            # Cursor history for stability fallback
            self._history.append((now, cx, cy))
            while self._history and now - self._history[0][0] > STABILITY_WINDOW:
                self._history.popleft()

            # Reading heuristic (cursor only — webcam can't detect this)
            if last_x is not None:
                dx = cx - last_x
                if 0 < dx < 60:
                    rightward_run += 1
                elif dx < -80:
                    rightward_run = 0
                else:
                    rightward_run = max(0, rightward_run - 1)
            last_x  = cx
            reading = rightward_run >= READING_MIN_RUN

            with self._lock:
                self._zone       = zone
                self._dwell_secs = dwell_secs
                self._stability  = stability
                self._reading    = reading
                self._on_screen  = on_screen
                self._blink_rate = blink_rate

            time.sleep(0.1)

    # ── public API ────────────────────────────────────────────────────────────

    def start(self) -> None:
        """Start background collection. Safe to call multiple times."""
        if self._running:
            return

        self._running = True
        self._thread  = threading.Thread(target=self._run, daemon=True,
                                         name="GazeCollector")
        self._thread.start()

        if USE_WEBCAM_GAZE and _MEDIAPIPE_OK:
            self._webcam_gaze = _WebcamGaze()
            print("[GazeCollector] Webcam gaze + blink estimation enabled "
                  f"(calibrating over {CALIBRATION_FRAMES} frames…)")
        else:
            reasons = []
            if not USE_WEBCAM_GAZE:
                reasons.append("USE_WEBCAM_GAZE != true")
            if not _MEDIAPIPE_OK:
                reasons.append("mediapipe/opencv not available or wrong version")
            print(f"[GazeCollector] Cursor-proxy mode "
                  f"({'; '.join(reasons)}).")

    def stop(self) -> None:
        """Stop background collection and release resources."""
        self._running = False
        if self._webcam_gaze is not None:
            self._webcam_gaze.stop()
            self._webcam_gaze = None

    def get_snapshot(self) -> dict:
        """
        Return the latest gaze snapshot.

        Keys
        ----
        gaze_zone        : str   — "center"|"top"|"bottom"|"left"|"right"|"corner"
        dwell_seconds    : float — seconds gaze has stayed in current zone
        gaze_stability   : float — 0 (jittery) … 1 (rock-steady)
        reading_detected : bool  — True when smooth L→R cursor drift found
        on_screen        : bool  — False when cursor has left the screen
        webcam_active    : bool  — True when iris tracking is running
        blink_rate       : float — blinks per minute (rolling 60 s window)
        """
        with self._lock:
            return {
                "gaze_zone":        self._zone,
                "dwell_seconds":    round(self._dwell_secs, 2),
                "gaze_stability":   self._stability,
                "reading_detected": self._reading,
                "on_screen":        self._on_screen,
                "webcam_active":    (
                    self._webcam_gaze is not None
                    and self._webcam_gaze.active
                ),
                "blink_rate":       self._blink_rate,
            }