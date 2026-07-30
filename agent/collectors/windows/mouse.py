import math
import threading
import time

from pynput import mouse


class MouseCollector:
    """
    Windows Mouse Collector.

    Tracks:
    - Mouse clicks
    - Mouse movement distance
    """

    def __init__(self):
        self.clicks = 0
        self.distance = 0.0

        self._lock = threading.Lock()
        self.listener = None

        self.last_position = None
        self.last_event_time = time.time()   # <-- Added

    def _on_move(self, x, y):

        with self._lock:

            self.last_event_time = time.time()   # <-- Added

            if self.last_position is not None:
                px, py = self.last_position
                self.distance += math.hypot(x - px, y - py)

            self.last_position = (x, y)

    def _on_click(self, x, y, button, pressed):

        if pressed:

            with self._lock:
                self.clicks += 1
                self.last_event_time = time.time()   # <-- Added

    def start(self):

        if self.listener is None:

            self.listener = mouse.Listener(
                on_move=self._on_move,
                on_click=self._on_click,
            )

            self.listener.start()

    def stop(self):

        if self.listener:
            self.listener.stop()
            self.listener = None

    def get_snapshot(self):

        with self._lock:

            snapshot = {
                "clicks": self.clicks,
                "distance": round(self.distance),
            }

            self.clicks = 0
            self.distance = 0.0

            return snapshot