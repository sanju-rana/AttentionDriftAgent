class AttentionScore:

    @staticmethod
    def compute(features: dict):

        score = 100

        score -= (
            features["fragmentation"] * 25
        )

        score -= (
            features["idle_ratio"] * 35
        )

        score += (
            features["gaze_ratio"] * 10
        )

        # Head turned away from the screen reduces focus (new)
        score -= (
            features.get("head_turn_ratio", 0) * 15
        )

        # Elevated blink rate (>30/min) signals fatigue / drift (new)
        blink_rate = features.get("blink_rate", 0)
        if blink_rate > 30:
            score -= min((blink_rate - 30) / 30, 1) * 10

        return max(
            0,
            min(100, score)
        )