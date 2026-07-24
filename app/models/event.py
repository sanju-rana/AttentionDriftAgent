from datetime import datetime
from pydantic import BaseModel


class Event(BaseModel):

    timestamp: datetime

    active_app: str

    active_url: str | None = None

    tab_switch: bool = False

    window_switch: bool = False

    idle_seconds: int = 0

    keystrokes: int = 0

    mouse_distance: float = 0

    mouse_clicks: int = 0

    scroll_distance: float = 0

    gaze_ratio: float = 1.0

    blink_rate: float = 0

    head_turn_ratio: float = 0