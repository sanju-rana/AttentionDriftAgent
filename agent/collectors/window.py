import subprocess


class WindowCollector:

    def __init__(self):
        self.last_window = None
        self.switch_count = 0

    def get_active_window(self):
        try:
            window_id = subprocess.check_output(
                ["xdotool", "getactivewindow"]
            ).decode().strip()

            title = subprocess.check_output(
                ["xdotool", "getwindowname", window_id]
            ).decode().strip()

            # fallback app name (IMPORTANT FIX)
            wm_class = subprocess.check_output(
                ["xprop", "-id", window_id, "WM_CLASS"]
            ).decode().strip()

            if self.last_window and self.last_window != title:
                self.switch_count += 1

            self.last_window = title

            return {
                "app": wm_class,
                "title": title
            }

        except Exception:
            return {
                "app": "unknown",
                "title": "unknown"
            }

    def get_and_reset_switches(self):
        count = self.switch_count
        self.switch_count = 0
        return count
    