import time


class IdleCollector:
    """
    Computes real idle time (seconds since the last keyboard or mouse event).

    Wraps the KeyboardCollector and MouseCollector instances so it can read
    their `last_event_time` without needing its own OS-level hooks. This
    works the same way on Windows, macOS, and Linux since it's built on
    pynput's listeners rather than a platform-specific "idle time" API.
    """

    def __init__(self, keyboard_collector=None, mouse_collector=None):
        self._keyboard = keyboard_collector
        self._mouse = mouse_collector
        self._start_time = time.time()

    def get_idle_seconds(self):
        last_times = [self._start_time]

        if self._keyboard is not None:
            last_times.append(self._keyboard.last_event_time)
        if self._mouse is not None:
            last_times.append(self._mouse.last_event_time)

        most_recent = max(last_times)
        return int(round(time.time() - most_recent))