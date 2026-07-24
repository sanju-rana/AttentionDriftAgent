from dataclasses import dataclass
from datetime import datetime

@dataclass
class ActivitySnapshot:
    timestamp: datetime

    active_app: str
    active_window: str

    key_count: int
    mouse_clicks: int
    mouse_distance: int

    idle_seconds: int

    window_switches: int

    gaze_zone: str = "center"
    gaze_stability: float = 1.0
    on_screen: bool = True
    blink_rate: float = 0.0

    focus_score: float = 0.0