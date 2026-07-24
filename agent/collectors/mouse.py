import threading
import time

from evdev import InputDevice, ecodes, list_devices


class MouseCollector:
    """
    Tracks real pointer clicks and movement via direct Linux kernel input
    events (evdev). Works under both X11 and Wayland.

    Movement is reported two different ways depending on hardware:
      - EV_REL (REL_X / REL_Y): traditional relative-motion mice.
      - EV_ABS (ABS_X/ABS_Y or ABS_MT_POSITION_X/Y): touchpads/clickpads,
        which report absolute finger position rather than deltas. Movement
        here is computed as the delta between successive absolute readings.
    """

    _ABS_AXIS_CODES = {
        ecodes.ABS_X,
        ecodes.ABS_Y,
        ecodes.ABS_MT_POSITION_X,
        ecodes.ABS_MT_POSITION_Y,
    }

    def __init__(self):
        self.clicks = 0
        self.distance = 0.0
        self._lock = threading.Lock()
        self.last_event_time = time.time()
        self._threads = []
        self._running = False

    def _find_pointer_devices(self):
        devices = []
        for path in list_devices():
            try:
                dev = InputDevice(path)
            except (OSError, PermissionError):
                continue
            caps = dev.capabilities(absinfo=False)
            rel = caps.get(ecodes.EV_REL, []) or []
            abs_codes = caps.get(ecodes.EV_ABS, []) or []
            keys = caps.get(ecodes.EV_KEY, []) or []

            has_rel = ecodes.REL_X in rel and ecodes.REL_Y in rel
            has_abs = (ecodes.ABS_X in abs_codes and ecodes.ABS_Y in abs_codes) or (
                ecodes.ABS_MT_POSITION_X in abs_codes and ecodes.ABS_MT_POSITION_Y in abs_codes
            )
            has_click = ecodes.BTN_LEFT in keys

            if has_rel or has_abs or has_click:
                devices.append(dev)
        return devices

    def _listen(self, device):
        last_vals = {}
        try:
            for event in device.read_loop():
                if not self._running:
                    break

                if event.type == ecodes.EV_REL:
                    if event.code in (ecodes.REL_X, ecodes.REL_Y):
                        with self._lock:
                            self.distance += abs(event.value)
                            self.last_event_time = time.time()

                elif event.type == ecodes.EV_ABS:
                    if event.code in self._ABS_AXIS_CODES:
                        prev = last_vals.get(event.code)
                        if prev is not None:
                            with self._lock:
                                self.distance += abs(event.value - prev)
                                self.last_event_time = time.time()
                        last_vals[event.code] = event.value

                elif event.type == ecodes.EV_KEY:
                    if event.code in (ecodes.BTN_LEFT, ecodes.BTN_RIGHT, ecodes.BTN_MIDDLE) \
                            and event.value == 1:
                        with self._lock:
                            self.clicks += 1
                            self.last_event_time = time.time()
        except OSError:
            pass

    def start(self):
        if self._threads:
            return
        self._running = True
        devices = self._find_pointer_devices()
        if not devices:
            print(
                "[MouseCollector] No readable pointer devices found under "
                "/dev/input. Make sure your user is in the 'input' group "
                "(sudo usermod -aG input $USER, then log out/in)."
            )
        for dev in devices:
            t = threading.Thread(target=self._listen, args=(dev,), daemon=True)
            t.start()
            self._threads.append(t)

    def stop(self):
        self._running = False
        self._threads = []

    def get_snapshot(self):
        with self._lock:
            data = {
                "clicks": self.clicks,
                "distance": round(self.distance),
            }
            self.clicks = 0
            self.distance = 0.0
            return data