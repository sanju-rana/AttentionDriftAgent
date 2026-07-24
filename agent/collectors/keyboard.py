import threading
import time

from evdev import InputDevice, categorize, ecodes, list_devices


class KeyboardCollector:
    """
    Counts real keypresses via direct Linux kernel input events (evdev).

    Works under both X11 and Wayland since it reads raw /dev/input/event*
    devices instead of going through the X server or the Wayland compositor.
    Requires the running user to have read access to /dev/input/event*
    (e.g. by being a member of the 'input' group).
    """

    def __init__(self):
        self.key_count = 0
        self._lock = threading.Lock()
        self.last_event_time = time.time()
        self._threads = []
        self._running = False

    def _find_keyboard_devices(self):
        keyboards = []
        for path in list_devices():
            try:
                dev = InputDevice(path)
            except (OSError, PermissionError):
                continue
            caps = dev.capabilities()
            keys = caps.get(ecodes.EV_KEY, [])
            # Heuristic: a real keyboard exposes a wide range of letter keys.
            if ecodes.KEY_A in keys and ecodes.KEY_SPACE in keys:
                keyboards.append(dev)
        return keyboards

    def _listen(self, device):
        try:
            for event in device.read_loop():
                if not self._running:
                    break
                if event.type == ecodes.EV_KEY:
                    key_event = categorize(event)
                    if key_event.keystate == key_event.key_down:
                        with self._lock:
                            self.key_count += 1
                            self.last_event_time = time.time()
        except OSError:
            pass

    def start(self):
        if self._threads:
            return
        self._running = True
        devices = self._find_keyboard_devices()
        if not devices:
            print(
                "[KeyboardCollector] No readable keyboard devices found under "
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

    def get_and_reset(self):
        with self._lock:
            count = self.key_count
            self.key_count = 0
            return count