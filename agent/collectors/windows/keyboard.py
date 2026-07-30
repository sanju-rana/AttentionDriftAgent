from pynput import keyboard
import time


class KeyboardCollector:
    """
    Windows keyboard collector.
    Counts key presses between snapshots.
    """

    def __init__(self):
        self.key_count = 0
        self.listener = None
        self.last_event_time = time.time()   # <-- add

    def _on_press(self, key):
        self.key_count += 1
        self.last_event_time = time.time()   # <-- add

    def start(self):
        if self.listener is None:
            self.listener = keyboard.Listener(
                on_press=self._on_press
            )
            self.listener.start()

    def stop(self):
        if self.listener:
            self.listener.stop()
            self.listener = None

    def get_and_reset(self):
        count = self.key_count
        self.key_count = 0
        return count