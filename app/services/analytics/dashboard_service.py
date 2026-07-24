from collections import defaultdict
from datetime import datetime, timezone


class DashboardService:

    @staticmethod
    def build_dashboard(events, interval_minutes=5):

        if not events:
            return {
                "summary": {},
                "averages": {},
                "trend": [],
                "apps": [],
                "interval_minutes": interval_minutes
            }

        # Bucket by absolute elapsed time (epoch seconds), not by
        # wall-clock minute. The old `minute // 20` approach only
        # worked for a hardcoded 20-minute window and produced wrong
        # buckets for any other interval (e.g. a 7-minute interval
        # crossing the top of the hour), since "minute" resets to 0
        # every hour regardless of the chosen interval.
        interval_seconds = max(1, interval_minutes) * 60

        buckets = defaultdict(list)

        for event in events:

            ts = event.timestamp
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)

            epoch = ts.timestamp()
            bucket_epoch = epoch - (epoch % interval_seconds)
            bucket_key = datetime.fromtimestamp(
                bucket_epoch, tz=ts.tzinfo
            )

            buckets[bucket_key].append(event)

        trend = []

        # Determine whether the trend spans more than one calendar day,
        # so labels can include the date instead of just "HH:MM" when
        # that would otherwise be ambiguous.
        all_dates = {ts.date() for ts in buckets.keys()}
        multi_day = len(all_dates) > 1
        label_format = "%b %d %H:%M" if multi_day else "%H:%M"

        for timestamp, bucket_events in sorted(
            buckets.items()
        ):

            avg_focus = 100

            if bucket_events:

                avg_idle = sum(
                    e.idle_seconds
                    for e in bucket_events
                ) / len(bucket_events)

                avg_focus -= min(
                    avg_idle * 2,
                    80
                )

                # Gaze signals (added from gaze.py data stored per event)
                avg_gaze_ratio = sum(
                    e.gaze_ratio
                    for e in bucket_events
                ) / len(bucket_events)

                avg_head_turn_ratio = sum(
                    e.head_turn_ratio
                    for e in bucket_events
                ) / len(bucket_events)

                avg_focus -= (1 - avg_gaze_ratio) * 10
                avg_focus -= avg_head_turn_ratio * 10

                avg_focus = max(0, min(100, avg_focus))

            trend.append(
                {
                    "timestamp":
                    timestamp.strftime(
                        label_format
                    ),
                    "timestamp_iso":
                    timestamp.isoformat(),
                    "score":
                    round(avg_focus, 2)
                }
            )

        app_usage = defaultdict(int)

        for e in events:
            app_usage[e.active_app] += 1

        apps = []

        total = len(events)

        for app, count in app_usage.items():

            apps.append(
                {
                    "app": app,
                    "percentage":
                    round(
                        count * 100 / total,
                        2
                    )
                }
            )

        average_focus = (
            sum(
                t["score"]
                for t in trend
            ) / len(trend)
        )

        # ── useful per-event averages (clicks, keystrokes, gaze, reading) ──
        avg_keystrokes = sum(
            e.keystrokes for e in events
        ) / total

        avg_clicks = sum(
            e.mouse_clicks for e in events
        ) / total

        avg_mouse_distance = sum(
            e.mouse_distance for e in events
        ) / total

        avg_gaze_score = sum(
            e.gaze_ratio for e in events
        ) / total

        avg_idle_seconds = sum(
            e.idle_seconds for e in events
        ) / total

        avg_blink_rate = sum(
            e.blink_rate for e in events
        ) / total

        reading_events = [
            e for e in events
            if getattr(e, "reading_detected", False)
        ]

        reading_ratio = len(reading_events) / total

        # Estimate average gap between consecutive events so we can turn
        # a count of "reading" events into an actual duration.
        ordered = sorted(events, key=lambda e: e.timestamp)
        if len(ordered) > 1:
            gaps = [
                (ordered[i].timestamp - ordered[i - 1].timestamp)
                .total_seconds()
                for i in range(1, len(ordered))
            ]
            avg_gap_seconds = sum(gaps) / len(gaps)
        else:
            avg_gap_seconds = 0

        avg_reading_minutes = (
            len(reading_events) * avg_gap_seconds
        ) / 60

        return {

            "summary": {

                "focus_score":
                round(
                    average_focus,
                    2
                ),

                "drift_score":
                round(
                    100 - average_focus,
                    2
                ),

                "event_count":
                len(events)
            },

            "averages": {
                "avg_keystrokes": round(avg_keystrokes, 2),
                "avg_clicks": round(avg_clicks, 2),
                "avg_mouse_distance": round(avg_mouse_distance, 2),
                "avg_gaze_score": round(avg_gaze_score * 100, 2),
                "avg_idle_seconds": round(avg_idle_seconds, 2),
                "avg_blink_rate": round(avg_blink_rate, 2),
                "reading_ratio": round(reading_ratio * 100, 2),
                "avg_reading_minutes": round(avg_reading_minutes, 2),
            },

            "trend": trend,

            "apps": apps,

            "interval_minutes": interval_minutes
        }