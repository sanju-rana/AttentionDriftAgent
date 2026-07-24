from app.services.features.feature_engineering import (
    FeatureEngineering
)

from app.services.scoring.attention_score import (
    AttentionScore
)


class SessionAnalyzer:

    def analyze(self, events):

        if not events:
            return {
                "focus_score": 0,
                "fragmentation": 0,
                "idle_ratio": 0
            }

        apps = [e.active_app for e in events]

        total_idle = sum(
            e.idle_seconds
            for e in events
        )

        earliest = min(
            e.timestamp
            for e in events
        )

        latest = max(
            e.timestamp
            for e in events
        )

        session_duration = max(
            (latest - earliest).total_seconds(),
            1
        )

        fragmentation = (
            FeatureEngineering
            .calculate_fragmentation(apps)
        )

        idle_ratio = min(
            total_idle / session_duration,
            1.0
        )

        gaze_ratio = (
            sum(
                e.gaze_ratio
                for e in events
            ) / len(events)
        )

        head_turn_ratio = (
            sum(
                e.head_turn_ratio
                for e in events
            ) / len(events)
        )

        blink_rate = (
            sum(
                e.blink_rate
                for e in events
            ) / len(events)
        )

        score = AttentionScore.compute(
            {
                "fragmentation": fragmentation,
                "idle_ratio": idle_ratio,
                "gaze_ratio": gaze_ratio,
                "head_turn_ratio": head_turn_ratio,
                "blink_rate": blink_rate,
            }
        )

        return {
            "focus_score": round(score, 2),
            "fragmentation": round(fragmentation, 4),
            "idle_ratio": round(idle_ratio, 4),
            "gaze_ratio": round(gaze_ratio, 4),
            "head_turn_ratio": round(head_turn_ratio, 4),
            "blink_rate": round(blink_rate, 2),
            "session_duration_seconds": session_duration,
            "event_count": len(events)
        }