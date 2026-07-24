from sqlalchemy import (
    Column,
    Integer,
    Float,
    String,
    Boolean,
    DateTime
)

from app.database.base import Base


class Event(Base):

    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)

    timestamp = Column(DateTime)

    active_app = Column(String)

    active_url = Column(String, nullable=True)

    tab_switch = Column(Boolean, default=False)

    window_switch = Column(Boolean, default=False)

    idle_seconds = Column(Integer, default=0)

    keystrokes = Column(Integer, default=0)

    mouse_distance = Column(Float, default=0)

    mouse_clicks = Column(Integer, default=0)

    scroll_distance = Column(Float, default=0)

    gaze_ratio = Column(Float, default=1)

    blink_rate = Column(Float, default=0)

    head_turn_ratio = Column(Float, default=0)