let trendChart = null;
let appChart = null;
let attentionPieChart = null;

function getSelectedInterval() {
    const select = document.getElementById("intervalSelect");
    return select ? select.value : 5;
}

async function loadDashboard() {
    try {
        const interval = getSelectedInterval();

        const response = await fetch(
            `/dashboard/metrics?interval_minutes=${interval}`
        );

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();

        console.log("Dashboard Data:", data);

        updateSummary(data);
        updateAverages(data.averages);
        drawTrendChart(data.trend || []);
        drawAppChart(data.apps || []);
        drawAttentionPie(data.summary || {});
        renderTimeline(data.trend || []);

    } catch (err) {
        console.error("Dashboard load failed:", err);
    }
}

function updateSummary(data) {
    if (!data || !data.summary) return;

    const focus = data.summary.focus_score ?? 0;
    const drift = data.summary.drift_score ?? 0;

    document.getElementById("focusScore").textContent =
        `${focus.toFixed(2)}%`;

    document.getElementById("driftScore").textContent =
        `${drift.toFixed(2)}%`;

    document.getElementById("eventCount").textContent =
        data.summary.event_count ?? 0;

    let status = "🟢 Focused";

    if (focus < 80) {
        status = "🟡 Moderate";
    }

    if (focus < 60) {
        status = "🔴 Distracted";
    }

    document.getElementById("sessionStatus").textContent =
        status;
}

function updateAverages(averages) {
    console.log("Averages:", averages);

    if (!averages) {
        console.error("No averages received");
        return;
    }

    document.getElementById("avgKeystrokes").textContent =
        averages.avg_keystrokes != null
            ? averages.avg_keystrokes.toFixed(2)
            : "--";

    document.getElementById("avgClicks").textContent =
        averages.avg_clicks != null
            ? averages.avg_clicks.toFixed(2)
            : "--";

    document.getElementById("avgGazeScore").textContent =
        averages.avg_gaze_score != null
            ? `${averages.avg_gaze_score.toFixed(2)}%`
            : "--";

    document.getElementById("avgBlinkRate").textContent =
        averages.avg_blink_rate != null
            ? `${averages.avg_blink_rate.toFixed(2)}/min`
            : "--";

    document.getElementById("readingRatio").textContent =
        averages.reading_ratio != null
            ? `${averages.reading_ratio.toFixed(2)}%`
            : "--";

    document.getElementById("avgReadingMinutes").textContent =
        averages.avg_reading_minutes != null
            ? `${averages.avg_reading_minutes.toFixed(2)} min`
            : "--";
}

function drawTrendChart(trend) {
    const labels = trend.map(item => item.timestamp);
    const scores = trend.map(item => item.score);

    const colorForScore = (score) => {
        if (score < 60) return "#ef4444";
        if (score < 80) return "#f59e0b";
        return "#10b981";
    };

    const pointColors = scores.map(colorForScore);

    if (trendChart) {
        trendChart.destroy();
    }

    const ctx = document.getElementById("trendChart").getContext("2d");

    const gradient = ctx.createLinearGradient(0, 0, 0, 380);
    gradient.addColorStop(0, "rgba(99, 102, 241, 0.35)");
    gradient.addColorStop(1, "rgba(99, 102, 241, 0.02)");

    trendChart = new Chart(
        ctx,
        {
            type: "line",
            data: {
                labels,
                datasets: [
                    {
                        label: "Focus Score",
                        data: scores,
                        borderColor: "#6366f1",
                        backgroundColor: gradient,
                        pointBackgroundColor: pointColors,
                        pointBorderColor: "#ffffff",
                        pointBorderWidth: 1.5,
                        pointRadius: trend.length > 60 ? 0 : 3,
                        pointHoverRadius: 6,
                        borderWidth: 2,
                        tension: 0.35,
                        fill: true
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: "index",
                    intersect: false
                },
                scales: {
                    y: {
                        min: 0,
                        max: 100,
                        ticks: {
                            callback: (value) => `${value}%`
                        },
                        grid: {
                            color: "#f1f5f9"
                        }
                    },
                    x: {
                        ticks: {
                            maxRotation: 0,
                            autoSkip: true,
                            maxTicksLimit: 12
                        },
                        grid: {
                            display: false
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: (context) =>
                                `Focus: ${context.parsed.y.toFixed(1)}%`
                        }
                    }
                }
            }
        }
    );
}

function drawAppChart(apps) {
    const labels = apps.map(app => app.app);
    const values = apps.map(app => app.percentage);

    if (appChart) {
        appChart.destroy();
    }

    appChart = new Chart(
        document.getElementById("appChart"),
        {
            type: "doughnut",
            data: {
                labels,
                datasets: [
                    {
                        data: values
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false
            }
        }
    );
}

function drawAttentionPie(summary) {
    if (attentionPieChart) {
        attentionPieChart.destroy();
    }

    attentionPieChart = new Chart(
        document.getElementById("attentionPieChart"),
        {
            type: "doughnut",
            data: {
                labels: ["Attention", "Drift"],
                datasets: [
                    {
                        data: [
                            summary.focus_score ?? 0,
                            summary.drift_score ?? 0
                        ]
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false
            }
        }
    );
}

function renderTimeline(trend) {
    const timeline =
        document.getElementById("timeline");

    timeline.innerHTML = "";

    trend
        .slice()
        .reverse()
        .forEach(item => {

            let cls = "focus-good";

            if (item.score < 80) {
                cls = "focus-medium";
            }

            if (item.score < 60) {
                cls = "focus-bad";
            }

            timeline.innerHTML += `
                <div class="timeline-item">
                    <div>
                        <div class="timeline-time">
                            ${item.timestamp}
                        </div>
                    </div>

                    <div class="${cls}">
                        ${item.score.toFixed(2)}%
                    </div>
                </div>
            `;
        });
}

const intervalSelect = document.getElementById("intervalSelect");
if (intervalSelect) {
    intervalSelect.addEventListener("change", loadDashboard);
}

loadDashboard();

setInterval(loadDashboard, 5000);