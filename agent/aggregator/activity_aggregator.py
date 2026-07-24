from datetime import datetime

from agent.models.activity_snapshot import (
    ActivitySnapshot
)

class ActivityAggregator:

    def build_snapshot(
        self,
        window_data,
        key_count,
        mouse_data,
        idle_seconds,
        window_switches,
        score,
        gaze_data=None
    ):
        gaze_data = gaze_data or {}
        return ActivitySnapshot(
            timestamp=datetime.utcnow(),
            active_app=window_data["app"],
            active_window=window_data["title"],
            key_count=key_count,
            mouse_clicks=mouse_data["clicks"],
            mouse_distance=mouse_data["distance"],
            idle_seconds=idle_seconds,
            window_switches=window_switches,
            gaze_zone=gaze_data.get("gaze_zone", "center"),
            gaze_stability=gaze_data.get("gaze_stability", 1.0),
            on_screen=gaze_data.get("on_screen", True),
            blink_rate=gaze_data.get("blink_rate", 0.0),
            focus_score=score
        )