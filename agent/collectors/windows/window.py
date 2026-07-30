import psutil
import win32gui
import win32process


class WindowCollector:
    """
    Windows implementation of WindowCollector.

    Returns the same format as the Linux collector:
    {
        "app": "...",
        "title": "..."
    }
    """

    def __init__(self):
        self.last_window = None
        self.switch_count = 0

    def get_active_window(self):

        hwnd = win32gui.GetForegroundWindow()

        title = win32gui.GetWindowText(hwnd)

        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            process = psutil.Process(pid)
            app = process.name()
        except Exception:
            app = "unknown"

        if self.last_window is not None and self.last_window != title:
            self.switch_count += 1

        self.last_window = title

        return {
            "app": app,
            "title": title
        }

    def get_and_reset_switches(self):

        count = self.switch_count
        self.switch_count = 0

        return count