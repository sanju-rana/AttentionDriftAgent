import platform

SYSTEM = platform.system()

if SYSTEM == "Windows":

    import win32api
    from pynput.mouse import Controller

    _mouse = Controller()

    def get_screen_size():
        return (
            win32api.GetSystemMetrics(0),
            win32api.GetSystemMetrics(1),
        )

    def get_cursor():
        return _mouse.position


elif SYSTEM == "Linux":

    import Xlib.display

    _display = Xlib.display.Display()
    _root = _display.screen().root

    def get_screen_size():
        screen = _display.screen()
        return (
            screen.width_in_pixels,
            screen.height_in_pixels,
        )

    def get_cursor():
        data = _root.query_pointer()
        return data.root_x, data.root_y


else:
    raise RuntimeError(f"Unsupported platform: {SYSTEM}")