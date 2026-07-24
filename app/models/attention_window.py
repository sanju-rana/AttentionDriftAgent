class AttentionScore:

    @staticmethod
    def compute(features: dict):

        score = 100

        score -= (
            features["fragmentation"] * 40
        )

        score -= (
            features["idle_ratio"] * 50
        )

        score += (
            features["gaze_ratio"] * 10
        )

        return max(
            0,
            min(100, score)
        )