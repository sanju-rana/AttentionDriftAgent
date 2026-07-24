from enum import Enum


class AttentionState(str, Enum):

    DEEP_FOCUS = "deep_focus"

    FOCUSED = "focused"

    EXPLORING = "exploring"

    DRIFTING = "drifting"

    DISTRACTED = "distracted"

    FATIGUED = "fatigued"

    ABSENT = "absent"