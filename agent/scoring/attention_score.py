class AttentionScore:

    @staticmethod
    def calculate(
        key_count,
        mouse_clicks,
        idle_seconds,
        window_switches,
        gaze_stability=1.0,
        on_screen=True,
        blink_rate=0.0,
    ):
        """
        Real-time agent-side focus score (0-100).

        gaze_stability, on_screen and blink_rate come from
        agent.collectors.gaze.GazeCollector.get_snapshot() and were
        previously not factored into the score at all.
        """
        score = 0

        # Input activity (rebalanced to make room for gaze signals)
        score += min(key_count / 100, 1) * 30
        score += min(mouse_clicks / 20, 1) * 15

        if idle_seconds < 10:
            score += 15

        if window_switches < 5:
            score += 15

        # ── gaze-based signals (new) ─────────────────────────────────
        # Steady gaze on screen contributes up to 15 pts.
        gaze_stability = max(0.0, min(1.0, gaze_stability))
        score += gaze_stability * 15

        # Looking at the screen at all is worth 10 pts.
        if on_screen:
            score += 10

        # Elevated blink rate (>30/min) is a fatigue / drift signal —
        # penalise up to 10 pts as it rises.
        if blink_rate > 30:
            score -= min((blink_rate - 30) / 30, 1) * 10

        return round(max(0.0, min(100.0, score)), 2)