# import platform

# SYSTEM = platform.system()

# if SYSTEM == "Linux":
#     from agent.collectors.linux.keyboard import KeyboardCollector
#     from agent.collectors.linux.mouse import MouseCollector
#     from agent.collectors.linux.window import WindowCollector

# elif SYSTEM == "Windows":
#     # Placeholder imports (we'll create these later)
#     from agent.collectors.windows.keyboard import KeyboardCollector
#     from agent.collectors.windows.mouse import MouseCollector
#     from agent.collectors.windows.window import WindowCollector

# else:
#     raise RuntimeError(f"Unsupported operating system: {SYSTEM}")

import platform

SYSTEM = platform.system()

if SYSTEM == "Linux":
    from agent.collectors.linux.keyboard import KeyboardCollector
    from agent.collectors.linux.mouse import MouseCollector
    from agent.collectors.linux.window import WindowCollector

elif SYSTEM == "Windows":
    from agent.collectors.windows.keyboard import KeyboardCollector
    from agent.collectors.windows.mouse import MouseCollector
    from agent.collectors.windows.window import WindowCollector

else:
    raise RuntimeError(f"Unsupported operating system: {SYSTEM}")