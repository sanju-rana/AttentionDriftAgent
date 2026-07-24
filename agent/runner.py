# import time

# from agent.config import COLLECTION_INTERVAL

# from agent.collectors.keyboard import (
#     KeyboardCollector
# )

# from agent.collectors.mouse import (
#     MouseCollector
# )

# from agent.collectors.idle import (
#     IdleCollector
# )

# from agent.collectors.window import (
#     WindowCollector
# )

# from agent.scoring.attention_score import (
#     AttentionScore
# )

# from agent.aggregator.activity_aggregator import (
#     ActivityAggregator
# )

# from agent.api.client import APIClient

# keyboard = KeyboardCollector()
# mouse = MouseCollector()
# idle = IdleCollector()
# window = WindowCollector()

# aggregator = ActivityAggregator()

# keyboard.start()
# mouse.start()

# while True:

#     window_data = window.get_active_window()

#     key_count = keyboard.get_and_reset()

#     mouse_data = mouse.get_snapshot()

#     idle_seconds = idle.get_idle_seconds()

#     score = AttentionScore.calculate(
#         key_count,
#         mouse_data["clicks"],
#         idle_seconds,
#         0
#     )

#     snapshot = aggregator.build_snapshot(
#         window_data,
#         key_count,
#         mouse_data,
#         idle_seconds,
#         0,
#         score
#     )

#     print(snapshot)

#     APIClient.send(snapshot)

#     time.sleep(COLLECTION_INTERVAL)




# import random
# import time
# from datetime import datetime

# from agent.api.client import APIClient

# while True:
#     payload = {
#     "timestamp": datetime.utcnow().isoformat(),


#         "active_app": random.choice([
#             "VS Code",
#             "Chrome",
#             "Terminal"
#         ]),

#         "active_window": random.choice([
#             "attention_score.py",
#             "feature_engineering.py",
#             "dashboard.html",
#             "terminal"
#         ]),

#         "key_count": random.randint(20, 100),
#         "mouse_clicks": random.randint(1, 20),
#         "mouse_distance": random.randint(100, 5000),
#         "idle_seconds": random.randint(0, 10),
#         "focus_score": random.randint(60, 100)
#     }

#     print(payload)

#     APIClient.send(payload)

#     time.sleep(5)




import time

from agent.config import COLLECTION_INTERVAL

from agent.collectors.keyboard import KeyboardCollector
from agent.collectors.mouse import MouseCollector
from agent.collectors.idle import IdleCollector
from agent.collectors.window import WindowCollector

from agent.scoring.attention_score import AttentionScore

from agent.aggregator.activity_aggregator import ActivityAggregator

from agent.api.client import APIClient

from agent.collectors.gaze import GazeCollector

keyboard = KeyboardCollector()
mouse = MouseCollector()
window = WindowCollector()
idle = IdleCollector(keyboard_collector=keyboard, mouse_collector=mouse)

aggregator = ActivityAggregator()

keyboard.start()
mouse.start()

gaze = GazeCollector()
gaze.start()

print("Attention Drift Agent started. Collecting real activity data every "
      f"{COLLECTION_INTERVAL}s. Press Ctrl+C to stop.")

try:
    while True:
        time.sleep(COLLECTION_INTERVAL)

        window_data = window.get_active_window()
        window_switches = window.get_and_reset_switches()

        key_count = keyboard.get_and_reset()
        mouse_data = mouse.get_snapshot()
        gaze_data = gaze.get_snapshot()
        idle_seconds = idle.get_idle_seconds()

        score = AttentionScore.calculate(
            key_count,
            mouse_data["clicks"],
            idle_seconds,
            window_switches,
            gaze_stability=gaze_data.get("gaze_stability", 1.0),
            on_screen=gaze_data.get("on_screen", True),
            blink_rate=gaze_data.get("blink_rate", 0.0),
        )

        snapshot = aggregator.build_snapshot(
            window_data,
            key_count,
            mouse_data,
            idle_seconds,
            window_switches,
            score,
            gaze_data,
        )

        print(snapshot)

        # APIClient.send(snapshot.__dict__ | {
        #     "timestamp": snapshot.timestamp.isoformat()
        # })


        payload = {
    "timestamp": snapshot.timestamp.isoformat(),

    "active_app": snapshot.active_app,

    "active_url": None,

    "tab_switch": False,

    "window_switch": window_switches > 0,

    "idle_seconds": idle_seconds,

    "keystrokes": key_count,

    "mouse_distance": mouse_data["distance"],

    "mouse_clicks": mouse_data["clicks"],

    "scroll_distance": 0,

    "gaze_ratio": gaze_data.get("gaze_stability", 0),

    "blink_rate": gaze_data.get("blink_rate", 0),

    "head_turn_ratio": (
        1 - gaze_data.get("gaze_stability", 0)
    ),

    "focus_score": score,
}

        print(payload)

        APIClient.send(payload)

except KeyboardInterrupt:
    print("\nStopping Attention Drift Agent...")
    keyboard.stop()
    mouse.stop()