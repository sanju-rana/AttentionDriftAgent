from collections import deque

from app.models.event import Event


class WindowManager:

    def __init__(self):

        self.events = deque(maxlen=10000)

    def add_event(self, event: Event):

        self.events.append(event)

    def get_recent_events(self):

        return list(self.events)

    def clear(self):

        self.events.clear()