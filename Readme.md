# Attention Drift Agent

A local cross-platform agent watches your own
keyboard, mouse, active window, and (optionally)
webcam-based gaze on your machine, computes a focus
score, and ships snapshots to a backend API that
stores them and serves a dashboard showing your
attention trend over time.

The project supports both Windows and Linux.

The project has two independent halves that run separately:

| Component | What it does | Where it runs |
|---|---|---|
| **Backend (`app/`)** | FastAPI service + Postgres DB + dashboard static files | Docker (recommended) |
| **Agent (`agent/`)** | Reads real input/window/webcam signals on *your* machine and POSTs events to the backend | Directly on your host, in a venv (needs hardware/device access Docker can't easily give it) |

---

## Supported Platforms

| Platform | Status |
|----------|--------|
| Windows | ✅ Supported |
| Linux | ✅ Supported |
| macOS | ⚠️ Experimental |

---
# 1. Local Development Setup

## Ubuntu Setup

### Install Git

```bash
sudo apt update
sudo apt install git
```

## Clone Repository
```bash
git clone https://github.com/jtanu1654/AttentionDriftAgent.git
cd AttentionDriftAgent
```

## Create virtual environment
```bash
python3 -m venv .venv
source .venv/bin/activate
```

## Install backend
```bash
pip install -r requirements.txt
```

## Install agent
```bash
cd agent
pip install -r requirements.txt
```

## Windows Setup

### Install Python

Install Python 3.11 or later from:

https://www.python.org/downloads/

During installation enable:

✓ Add Python to PATH

### Clone repository

```bash
git clone https://github.com/jtanu1654/AttentionDriftAgent.git
cd AttentionDriftAgent
```

### Create virtual environment

```bash
python -m venv .venv
```

### Activate

```cmd
.venv\Scripts\activate.bat
```

Deactivate when finished:

```bash
deactivate
```

### Install backend dependencies

```bash
pip install -r requirements.txt
```

### Install agent dependencies

```bash
cd agent
pip install -r requirements.txt
```

---

## ## Ubuntu (Linux Only): Login Session

When logging into Ubuntu (especially inside VirtualBox/VMware), select

**Ubuntu on Xorg**

instead of

**Ubuntu**

This ensures better compatibility with:

- Xlib
- xdotool
- xprop
- evdev
- Active window detection
- Cursor tracking

These components are required by the Attention Drift Agent.

<img width="1600" height="877" alt="image" src="https://github.com/user-attachments/assets/d7d625ac-c288-4d4e-bb51-8b62099ead20" />

---

## Project Structure

```text
AttentionDriftAgent/

├── app/
│   ├── api/
│   ├── models/
│   ├── repository/
│   ├── services/
│   └── main.py
│
├── dashboard/
│
├── agent/
│   ├── collectors/
│   │   ├── common/
│   │   ├── linux/
│   │   ├── windows/
│   │   └── factory.py
│   │
│   ├── platform/
│   │   └── screen.py
│   │
│   ├── runner.py
│   └── requirements.txt
│
├── docker-compose.yml
└── requirements.txt
```

---

# 2. Overview

```
┌──────────────────────────      POST /events              ┌───────────────────────┐
│   Cross-platform Agent   │ ─────────────────────────▶️   |   Backend API (api)   │
│                          |                               │   FastAPI + Postgres  │
│ keyboard/mouse           |                               │                       │
│ active window            |                               │  scoring, bucketing,  │
│ webcam gaze/blink        |                               │  /dashboard/metrics   │
└──────────────────────────┘                               └──────────┬────────────┘
                                                                      │ serves
                                                                      ▼
                                                            ┌──────────────────────┐
                                                            │ Dashboard (/ui)       │
                                                            │ trend chart, app mix, │
                                                            │ timeline, averages    │
                                                            └──────────────────────┘
```

**Agent collectors** (`agent/collectors/`)

- `common/`
  - `gaze.py` – Shared gaze tracking and blink detection
  - `idle.py` – Tracks user idle time

- `linux/`
  - `keyboard.py`
  - `mouse.py`
  - `window.py`

- `windows/`
  - `keyboard.py`
  - `mouse.py`
  - `window.py`

- `factory.py`
  - Automatically selects the appropriate collector implementation for the current operating system.

Every `COLLECTION_INTERVAL` seconds (default 5s, `agent/config.py`), the agent
aggregates a snapshot, computes a local real-time score, and POSTs it to
`POST /events` on the backend.

**Backend** stores each event, and `app/services/analytics/dashboard_service.py`
buckets recent events into time windows (configurable interval, default 5 min)
to build the trend line, app-usage breakdown, and summary stats served at
`GET /dashboard/metrics`.


---

# 3. Running the backend (Docker)

The backend (FastAPI + Postgres) is the easiest part to run — it's fully
containerized.

**Prerequisites:** Docker + Docker Compose installed.
 
## Linux
```bash
# from the project root
cp .env.example .env   # then fill in/check values, see below
docker compose up --build
```

## WIndows
```bash
copy .env.example .env
docker compose up --build
```


`.env` (used by `docker-compose.yml` and `app/core/config.py`):

```env
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/attention_db
APP_NAME=Attention Drift Agent
WINDOW_SIZE_SECONDS=300
SNAPSHOT_INTERVAL_SECONDS=30
```

This brings up two containers:
- `attention-api` — FastAPI app on `http://localhost:8000`
- `attention-postgres` — Postgres 17 on `localhost:5432`

Once running:
- API docs: `http://localhost:8000/docs`
- Dashboard: `http://localhost:8000/ui/index.html`
- Health check: `http://localhost:8000/health`

`docker-compose.yml` mounts `./app` and `./dashboard` as live volumes, so
backend/dashboard code edits are picked up without rebuilding the image
(uvicorn isn't run with `--reload` by default — restart the `api` container
to pick up Python changes: `docker compose restart api`).


---

# 4. Running the agent (directly on your machine, via venv)

The agent needs to read raw input devices and (optionally) your webcam —
that's awkward to do from inside Docker, so it's meant to run directly on
your host in its own virtual environment, separate from the backend.

### 4a. Linux system packages

```bash
sudo apt update
sudo apt install -y \
    python3-venv python3-dev build-essential \
    xdotool x11-utils \
    libx11-6 libxtst6 \
    v4l-utils \
    libgl1 libglib2.0-0
```

What each is for:
- `xdotool`, `x11-utils` (provides `xprop`) — active window title/app detection
- `libx11-6`, `libxtst6` — needed by `python-xlib` (cursor position for the fallback gaze proxy)
- `v4l-utils` — webcam access for gaze/blink tracking
- `libgl1`, `libglib2.0-0` — runtime libs `opencv-python`/`mediapipe` need even headless

Give your user permission to read raw input devices (required by `evdev`):

```bash
sudo usermod -aG input $USER
# then log out and back in for the group change to take effect
```

### 4b. Python virtual environment

#### Linux
```bash
cd agent
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

#### Windows
```cmd
cd agent
python -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt
```

Optional — enable real webcam-based gaze + blink tracking (otherwise it
falls back to a cursor-position proxy, no webcam needed):

#### Linux
```bash
export USE_WEBCAM_GAZE=true   # default is already true; set to false to disable
```
#### Windows (Command Prompt)
```bash
set USE_WEBCAM_GAZE=true  # default is already true; set to false to disable
```

#### Windows (PowerShell)
```bash
$env:USE_WEBCAM_GAZE="true"   # default is already true; set to false to disable
```

### 4c. Point it at your backend and run

`agent/api/client.py` posts to `http://localhost:8000/events` and
`agent/config.py` controls the collection interval — edit these if your
backend isn't on localhost:8000.

```bash
python -m agent.runner
```

The correct collectors are selected automatically
based on the operating system.

You should see snapshots being collected and POSTed every
`COLLECTION_INTERVAL` seconds. Press `Ctrl+C` to stop.

---

# 5. How the score is calculated (and why)

There are **two** scoring implementations in this codebase, intentionally:

### Agent-side (`agent/scoring/attention_score.py`) — real-time, per-snapshot

Runs every 5s on the agent with whatever it has *right now* (no history):

| Signal | Max points | Why |
|---|---|---|
| Keystrokes (capped at 100/interval) | 30 | Strongest, cheapest-to-measure proxy for active engagement |
| Mouse clicks (capped at 20/interval) | 15 | Secondary input-activity signal |
| Idle < 10s | 15 | Binary "are you even at the keyboard" check |
| Window switches < 5 | 15 | Frequent app/window switching is a classic context-fragmentation signal |
| Gaze stability (0–1) | 15 | Steady gaze (low iris/cursor jitter) suggests sustained attention |
| On-screen (cursor within bounds) | 10 | Cheap binary signal you're at the machine at all |
| Blink rate penalty (>30/min) | −10 | Elevated blink rate is a known fatigue/drift indicator |

Total caps at 100, floors at 0.

### Backend-side (`app/services/scoring/attention_score.py`) — windowed/aggregated

Runs over a *window* of events (`app/services/features/feature_engineering.py`
computes window-level features first) and starts from 100, then subtracts:

| Feature | Weight | Why |
|---|---|---|
| `fragmentation` (ratio of app switches in the window) | −25 | Task-switching rate over a window is a more reliable fragmentation signal than a single snapshot |
| `idle_ratio` (fraction of window spent idle) | −35 | Idle time is the single strongest drift indicator available without a webcam |
| `gaze_ratio` | +10 | Rewards sustained on-screen gaze across the window |
| `head_turn_ratio` | −15 | Head turned away from screen — stronger drift signal than eye jitter alone |
| Blink rate penalty (>30/min) | −10 | Same fatigue heuristic as the agent-side score |

### Why a hand-weighted heuristic formula (not a trained model)?

- **No labeled data yet.** There's no ground-truth "was this person actually
  focused" dataset to train against — the project doesn't have a labeling
  pipeline, model registry, or training infra (see Future Scope).
- **Interpretability.** Every point gained or lost can be explained to the
  person looking at their own dashboard ("you lost 15 points because you were
  idle for most of that window"). A black-box model score would be harder to
  trust for a self-quantification tool.
- **Cheap to compute in real time.** The agent recomputes a score every 5
  seconds on a regular laptop; a weighted sum needs no inference runtime.
  The backend's windowed version is similarly just arithmetic over a list of
  events, no model loading.
- **Easy to tune.** Weights are plain constants, so they can be adjusted
  (or made configurable per user) without retraining anything.
- **Two-tier design on purpose.** The agent-side formula is shaped to work
  with a single noisy snapshot (no history available locally), while the
  backend-side formula is shaped to work with aggregated window features
  (ratios over many events), which is why the weight distribution differs
  between the two even though they're measuring similar underlying signals.

The tradeoff: hand-set weights are a guess, not a fit — they encode the
authors' intuition about what "focused" looks like, not anything learned
from real outcomes. That's the main thing the future ML work below is meant
to fix.

---
# 6. Sample Image from Dashboard
<img width="1849" height="950" alt="image" src="https://github.com/user-attachments/assets/9efb753d-822a-45f8-9d20-e854fb8a7578" />
---

# 7. Future scope

The `Filestructure` file in this repo sketches a much larger architecture
than what's currently implemented — most of it isn't built yet. Notable gaps
and planned directions:

**Scoring & ML**
- `app/ml/` (feature store, trainer, predictor, model registry) — replace/augment
  the hand-weighted formula with a model trained on real outcome labels once
  there's enough data and a way to collect labels (e.g. a periodic
  "were you focused?" self-report prompt).
- `productivity_score.py`, `distraction_score.py`, `fatigue_score.py` —
  split the single focus score into separate, more specific scores.
- Per-user baselines (`user_baseline.py`, `baseline_features.py`) — score
  relative to *your* normal idle/keystroke patterns instead of fixed
  constants that don't account for e.g. people who read a lot vs. type a lot.

**Drift detection & intervention**
- `drift_detector.py` / `root_cause_analyzer.py` / `drift_predictor.py` —
  detect when a drift is starting (not just report the score after the
  fact) and predict it before it happens.
- `intervention_engine.py` / `recommendation_engine.py` — nudge the user
  ("you've been idle 10 min, want a break reminder?") instead of being
  purely passive/observational.
- `attention_state_machine.py` — model focus as states with transition rules
  (focused → drifting → distracted → recovering) instead of a single
  continuous score.

**Platform & collection**
- Enhance Windows and Linux collector support with
additional browser-level telemetry and platform-
specific optimizations.
- Browser extension for tab-level URL/title (the schema already has
  `active_url`/`tab_switch` fields that nothing currently populates).

**Backend infra**
- `alembic/versions/` — migrations aren't set up yet despite `alembic.ini`
  being present; schema changes currently rely on `Base.metadata.create_all`.
- `tests/` — no automated tests yet for scoring, API, or repositories.
- Auth (`core/security.py`) — currently there's no authentication on any
  endpoint; fine for a single-user local setup, not for anything multi-user
  or remotely hosted.
- Raise the hardcoded `limit=1000` in `EventRepository.get_recent` (or add
  pagination/date-range params) — at fine-grained trend intervals over long
  sessions, 1000 events stops covering a full day.

**Dashboard**
- Date-range picker (today / this week / custom range) rather than always
  "most recent 1000 events."
- Export trend data (CSV/JSON) for the user's own analysis.
