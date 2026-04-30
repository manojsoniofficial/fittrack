# 🏋️ FitTrack Pro
## Smart Workout, Nutrition & Progress Manager for HealthHub
### MCS504 Software Development Methodologies — Assessment 3 | B2 2026

![Coverage](coverage_reports/coverage-badge.svg)

---

## 📋 Project Overview

FitTrack Pro is a full-stack fitness tracking platform built for the fictional health-tech startup **HealthHub**. It combines a **PyQt6 desktop application**, a **Flask REST API**, and a **PostgreSQL 15 database** to give users a complete tool for managing workouts, nutrition, body measurements, and fitness goals.

The project simulates a full Agile software engineering lifecycle — requirements analysis, UML modelling, architecture design, implementation, testing, and a live demonstration — delivered across **two 2-week Scrum sprints**.

---

## 🏗️ Architecture: Layered + Ports-and-Adapters (Hexagonal)

```
┌──────────────────────────────────────────────────────────────────┐
│                        UI Layer  (Adapters)                      │
│         PyQt6 Desktop Client          Flask REST API             │
│            (views/)               (api/routes/*.py)              │
├──────────────────────────────────────────────────────────────────┤
│                      Service Layer  (Ports)                      │
│   CalorieCalculator │ ProgressAnalyser │ BadgeService            │
│              NutritionAdapter (external API + cache)             │
├──────────────────────────────────────────────────────────────────┤
│                     Domain Layer  (Core)                         │
│  User │ FitnessGoal │ WorkoutSession │ Exercise │ MealEntry      │
│  BodyMeasurement │ ProgressReport │ Badge │ Notification         │
├──────────────────────────────────────────────────────────────────┤
│                  Infrastructure Layer  (Adapters)                │
│   SQLite via SQLAlchemy (desktop)  │  PostgreSQL 15 (API/Docker) │
│   Flask-Migrate (Alembic)          │  requests-cache (Nutrition) │
└──────────────────────────────────────────────────────────────────┘
```

**Why this architecture?** Separating the domain from adapters means the Flask REST API, PyQt6 client, and database driver can all be swapped independently. The nutrition adapter, for example, calls the Edamam external API when a key is configured and silently falls back to a built-in food database when it is not — the rest of the system never notices the difference.

---

## 📁 Project Structure

```
fittrack_pro/
│
├── main.py                        ← PyQt6 desktop app entry point
├── run_api.py                     ← Flask API entry point + CLI commands
├── manage_db.py                   ← DB management CLI (create/seed/reset)
├── seed_data.py                   ← Standalone data seeder
│
├── requirements.txt               ← Desktop client dependencies (PyQt6)
├── requirements-api.txt           ← Flask API dependencies
├── requirements-test.txt          ← Testing dependencies
├── .env.example                   ← Environment variable template
│
│── models/                        ← Domain layer (shared by desktop + API)
│   ├── database.py                ← 9 ORM models + SQLite init + demo seed
│   └── services.py                ← CalorieCalculator, ProgressAnalyser, BadgeService
│
├── api/                           ← Flask REST API (adapter layer)
│   ├── __init__.py                ← App factory, extensions, error handlers
│   ├── config.py                  ← Dev / Testing / Production configs
│   ├── models.py                  ← Flask-SQLAlchemy models (PostgreSQL)
│   ├── badge_service.py           ← Badge award logic (Flask session)
│   ├── nutrition_adapter.py       ← External Nutrition API + fallback cache
│   └── routes/
│       ├── auth.py                ← POST /register, /login, /refresh, GET /me
│       ├── workouts.py            ← CRUD + offline sync
│       ├── nutrition.py           ← CRUD + food search + offline sync
│       ├── goals.py               ← CRUD
│       ├── measurements.py        ← CRUD + auto-goal update
│       ├── progress.py            ← Weekly summary + report generation
│       ├── coach.py               ← Client list, summaries, report export
│       └── notifications.py       ← CRUD + mark-read
│
├── views/                         ← PyQt6 UI (adapter layer)
│   ├── login_view.py              ← Login screen with dark theme
│   ├── main_window.py             ← Sidebar navigation + stacked pages
│   ├── dashboard_view.py          ← Stats cards, bar chart, pie chart
│   ├── workout_view.py            ← Workout CRUD + exercises sub-table
│   ├── nutrition_view.py          ← Meal logging + macro progress bar
│   └── other_views.py             ← Goals, Measurements, Notifications, Coach
│
├── assets/
│   └── styles.py                  ← Full dark-theme Qt stylesheet
│
├── tests/
│   ├── test_suite.py              ← 44 tests: Unit + Integration + Acceptance
│   └── test_api.py                ← 51 Flask API tests (all endpoints)
│
├── docker/
│   └── postgres/
│       └── init.sql               ← Create fittrack_dev + fittrack_test DBs
│
├── Dockerfile                     ← Multi-stage production image (gunicorn)
├── Dockerfile.test                ← Test runner image
├── docker-compose.yml             ← PostgreSQL 15 + Flask API
├── docker-compose.test.yml        ← Isolated test environment with Postgres
│
└── .github/
    └── workflows/
        └── ci.yml                 ← 4-job CI: unit tests, API tests,
                                      Postgres integration, Docker build
```

---

## 🚀 Quick Start

### Option A — Desktop App Only (PyQt6 + SQLite)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Launch the app (auto-creates SQLite DB and seeds demo data)
python main.py
```

### Option B — Flask API Only (no Docker)

```bash
# 1. Install API dependencies
pip install -r requirements-api.txt

# 2. Copy and configure environment
cp .env.example .env
# Edit .env: set DATABASE_URL to a local PostgreSQL instance or leave as SQLite

# 3. Initialise database
python manage_db.py --create
python manage_db.py --seed

# 4. Start dev server (http://localhost:5000)
python run_api.py
```

### Option C — Full Stack with Docker ✅ Recommended

```bash
# 1. Copy environment file
cp .env.example .env

# 2. Build and start all services
docker compose up --build

# Services started:
#   Flask API   → http://localhost:5000
#   PostgreSQL  → localhost:5432

# 3. Seed demo data (runs automatically on first start)
#    Or run manually:
docker compose exec api flask --app run_api seed-db
```

### Login Credentials

| Username | Password | Role |
|---|---|---|
| `john_doe` | `user123` | Member |
| `coach_sarah` | `coach123` | Coach |

---

## 🌐 REST API Reference

All endpoints require `Authorization: Bearer <token>` except `/api/auth/register`, `/api/auth/login`, and `/api/health`.

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/auth/register` | Register new user |
| `POST` | `/api/auth/login` | Login → access + refresh tokens |
| `POST` | `/api/auth/refresh` | Refresh access token |
| `GET` | `/api/auth/me` | Current user profile |

### Workouts

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/workouts` | List workouts (filter: `activity_type`, `start_date`, `end_date`) |
| `POST` | `/api/workouts` | Log workout (auto-calculates calories if omitted) |
| `GET` | `/api/workouts/<id>` | Get single workout + exercises |
| `PUT` | `/api/workouts/<id>` | Update workout |
| `DELETE` | `/api/workouts/<id>` | Delete workout |
| `POST` | `/api/workouts/sync` | Batch sync offline-queued workouts |

### Nutrition

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/nutrition` | List meals (filter: `date`, `meal_type`) |
| `POST` | `/api/nutrition` | Log meal (auto-fetches nutrition if calories omitted) |
| `GET` | `/api/nutrition/summary` | Daily macro totals (`?date=YYYY-MM-DD`) |
| `GET` | `/api/nutrition/search` | Food search via adapter (`?q=chicken&qty=1`) |
| `GET` | `/api/nutrition/<id>` | Get single meal |
| `PUT` | `/api/nutrition/<id>` | Update meal |
| `DELETE` | `/api/nutrition/<id>` | Delete meal |
| `POST` | `/api/nutrition/sync` | Batch sync offline-queued meals |

### Goals

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/goals` | List fitness goals |
| `POST` | `/api/goals` | Create goal |
| `PUT` | `/api/goals/<id>` | Update goal (can mark `is_completed: true`) |
| `DELETE` | `/api/goals/<id>` | Delete goal |

### Measurements

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/measurements` | List body measurements |
| `POST` | `/api/measurements` | Log measurement (auto-updates linked weight goals) |
| `GET` | `/api/measurements/<id>` | Get single measurement |
| `PUT` | `/api/measurements/<id>` | Update measurement |
| `DELETE` | `/api/measurements/<id>` | Delete measurement |

### Progress

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/progress/users/<id>/progress` | Weekly summary (`start_date`, `end_date` params) |
| `POST` | `/api/progress/users/<id>/report` | Generate and persist ProgressReport |

### Coach

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/coach/clients` | List all clients assigned to this coach |
| `GET` | `/api/coach/clients/<id>/summary` | Client stats: workouts, calories, weight, streak |
| `POST` | `/api/coach/clients/<id>/report` | Generate progress report for a client |

### Notifications

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/notifications` | List notifications (`?unread_only=true`) |
| `POST` | `/api/notifications` | Create reminder |
| `PATCH` | `/api/notifications/<id>/read` | Mark single notification as read |
| `POST` | `/api/notifications/read-all` | Mark all notifications as read |
| `DELETE` | `/api/notifications/<id>` | Delete notification |

### Health

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Returns `{ status, service, database, version }` |

---

## ✨ Feature List

### Member (PyQt6 Desktop)
| Feature | Details |
|---------|---------|
| **Dashboard** | Stat cards (workouts, calories burned/in, streak), weekly bar chart, macro pie chart, active goals with progress bars, recent activity feed, badge showcase |
| **Workout Tracker** | Full CRUD, exercise sub-table per session, auto-calorie estimate (MET formula), filter by type and period |
| **Nutrition Logger** | Log by meal type, 14 food presets with quick-fill, macro progress bar, daily calorie target tracking |
| **Body Measurements** | Weight, body fat %, muscle mass, waist/chest/hips; weight trend spline chart (QDateTimeAxis) |
| **Fitness Goals** | CRUD with progress bars, auto-complete when target reached via measurement |
| **Notifications** | Schedule workout/meal/measurement reminders, mark read, unread count badge |
| **Offline Support** | Workouts and meals stored with `is_synced=False`; synced via API on reconnect |
| **Badge System** | 7 auto-awarded badges: First Workout, Workout Warrior, Iron Will, Consistency Star, Goal Crusher, Marathon Month, Calorie Counter |

### Coach (PyQt6 Desktop)
| Feature | Details |
|---------|---------|
| **Client List** | Sidebar shows all assigned clients |
| **Client Detail** | Workouts this month, avg daily calories, weight change, streak |
| **Export Reports** | Progress CSV and PDF via Qt printer (`QPrinter`) |

### Flask REST API
| Feature | Details |
|---------|---------|
| **JWT Auth** | Access + refresh tokens, 24h expiry, proper error handlers |
| **Auto-calorie calc** | `POST /workouts` without `calories_burned` auto-estimates using MET + user weight |
| **Nutrition adapter** | `GET /nutrition/search` queries Edamam API (with `requests-cache`) or falls back to built-in 25-food database |
| **Offline sync** | `POST /workouts/sync` and `POST /nutrition/sync` accept batches of offline entries |
| **Auto-goal update** | `POST /measurements` updates `current_value` on linked weight goals and auto-completes when target is reached |
| **Coach endpoints** | Role-protected; 403 for non-coaches; 404 for unassigned clients |
| **Rate limiting** | `requests-cache` prevents hammering the external nutrition API |

---

## 🗃️ Database Models

| Model | Key Fields |
|-------|-----------|
| `User` | `username`, `email`, `password_hash`, `role`, `coach_id`, `is_active` |
| `FitnessGoal` | `goal_type`, `target_value`, `current_value`, `unit`, `target_date`, `is_completed` |
| `WorkoutSession` | `name`, `activity_type`, `duration_minutes`, `calories_burned`, `is_synced` |
| `Exercise` | `name`, `sets`, `reps`, `weight_kg`, `duration_seconds` (linked to WorkoutSession) |
| `MealEntry` | `meal_type`, `food_name`, `calories`, `protein_g`, `carbs_g`, `fat_g`, `is_synced` |
| `BodyMeasurement` | `weight_kg`, `body_fat_percent`, `muscle_mass_kg`, `waist_cm`, `chest_cm`, `hips_cm` |
| `ProgressReport` | `period_start/end`, `total_workouts`, `total_calories_burned`, `weight_change_kg`, `generated_by` |
| `Badge` | `name`, `description`, `icon`, `awarded_at` |
| `Notification` | `title`, `message`, `reminder_type`, `scheduled_at`, `is_read`, `is_sent` |

---

## 🧪 Running Tests

### Unit + Integration + Acceptance Tests (no database required)

```bash
pip install -r requirements.txt -r requirements-test.txt

# All 44 tests
pytest tests/test_suite.py -v

# With coverage
pytest tests/test_suite.py -v --cov=models --cov-report=term-missing

# Individual test classes
pytest tests/test_suite.py::TestCalorieCalculator -v
pytest tests/test_suite.py::TestProgressAnalyser -v
pytest tests/test_suite.py::TestAcceptanceScenarios -v
```

### Flask API Tests (SQLite in-memory — no Postgres needed)

```bash
pip install -r requirements-api.txt -r requirements-test.txt

# All 51 API tests
pytest tests/test_api.py -v

# With coverage
pytest tests/test_api.py -v --cov=api --cov-report=term-missing

# Individual test classes
pytest tests/test_api.py::TestAuth -v
pytest tests/test_api.py::TestWorkouts -v
pytest tests/test_api.py::TestOfflineSync -v
pytest tests/test_api.py::TestCoach -v
```

### Both suites together

```bash
pytest tests/ -v --cov=api --cov=models --cov-report=term-missing --cov-fail-under=80
```

### Integration tests against real PostgreSQL (Docker)

```bash
docker compose -f docker-compose.test.yml up --abort-on-container-exit
docker compose -f docker-compose.test.yml down -v
```

### Coverage Badge (Auto-updated by CI)

```bash
# Windows (local): run the same batch used by CI
coverage_reports\run_coverage.bat
```

What happens on GitHub:
- The `coverage-badge` job in `.github/workflows/ci.yml` runs after tests.
- It generates `coverage_reports/coverage.xml` + `coverage_reports/coverage-badge.svg`.
- On pushes to `main`/`develop`, CI commits updated `coverage-badge.svg` so the README badge refreshes automatically.

### Test Coverage Summary

| Suite | File | Tests | What's Covered |
|-------|------|-------|----------------|
| Unit | `test_suite.py` | 17 | CalorieCalculator (BMR, TDEE, MET, macros), WorkoutSession.total_duration(), password hashing, FitnessGoal, BadgeService |
| Integration | `test_suite.py` | 11 | Full workout+badge flow, meal+summary, measurement→goal, multi-week report, coach access |
| Acceptance | `test_suite.py` | 16 | Offline meal sync, offline workout sync, coach export, workout/meal reminders, full goal scenario |
| API Auth | `test_api.py` | 8 | Register, duplicate check, login, wrong password, /me, health check |
| API Workouts | `test_api.py` | 10 | CRUD, auto-calories, exercises, filter, cross-user security |
| API Offline Sync | `test_api.py` | 4 | Sync meals, sync workouts, empty sync, retrievability |
| API Nutrition | `test_api.py` | 7 | Log meal, adapter fallback, search, summary, CRUD |
| API Goals | `test_api.py` | 3 | Create, update completion, delete |
| API Measurements | `test_api.py` | 4 | Add, auto-goal update, list, delete |
| API Progress | `test_api.py` | 3 | Summary, report generation, cross-user security |
| API Notifications | `test_api.py` | 6 | Create workout/meal reminders, list, mark read, mark all, delete |
| API Coach | `test_api.py` | 5 | List clients, export report, summary, non-coach blocked, unassigned client 404 |
| **Total** | | **95** | |

---

## 📊 Business Logic

### CalorieCalculator — Mifflin-St Jeor Equation

```
BMR (Male)   = 10 × weight_kg + 6.25 × height_cm − 5 × age + 5
BMR (Female) = 10 × weight_kg + 6.25 × height_cm − 5 × age − 161
TDEE         = BMR × Activity Multiplier
Calories Burned = MET × weight_kg × (duration_minutes / 60)
```

| Activity Level | Multiplier |
|----------------|-----------|
| Sedentary | 1.20 |
| Light | 1.375 |
| Moderate | 1.55 |
| Active | 1.725 |
| Very Active | 1.90 |

| Activity Type | MET Value |
|---------------|-----------|
| HIIT | 8.5 |
| Sports | 7.5 |
| Cardio | 7.0 |
| Strength Training | 5.0 |
| Other | 5.0 |
| Yoga | 3.0 |

### Nutrition Adapter — Priority Chain

```
1. Edamam Food Database API  (when NUTRITION_APP_ID + NUTRITION_API_KEY are set)
       ↓  requests-cache (1 hour TTL, avoids redundant calls)
2. Built-in fallback food database  (25 common foods, always available)
3. Zero values  (unknown food — caller still gets a valid dict back)
```

### Badge Criteria

| Badge | Trigger |
|-------|---------|
| First Workout | 1 workout logged |
| Workout Warrior | 10 workouts logged |
| Iron Will | 50 workouts logged |
| Consistency Star | 7 workouts this calendar month |
| Marathon Month | 300+ workout minutes this month |
| Goal Crusher | 1 goal marked completed |
| Calorie Counter | Meals logged for 7 days |

---

## 🏃 Scrum Sprint Plan

### Sprint 1 — Weeks 1–2: Core Foundation

| Story | Description |
|-------|-------------|
| US-01 | User registration and secure login (PyQt6 + JWT) |
| US-02 | SQLAlchemy domain models + PostgreSQL schema |
| US-03 | Dashboard with stat cards and weekly bar chart |
| US-04 | Log workout sessions with exercises |
| US-05 | Flask REST API skeleton + auth endpoints |
| US-06 | `POST /api/workouts` with auto-calorie calculation |

### Sprint 2 — Weeks 3–4: Advanced Features + Testing

| Story | Description |
|-------|-------------|
| US-07 | Nutrition logging + macro tracking |
| US-08 | External nutrition API adapter with cache fallback |
| US-09 | Body measurements + weight trend chart |
| US-10 | Fitness goals with progress tracking + auto-completion |
| US-11 | Coach dashboard: client list, stats, CSV/PDF export |
| US-12 | Notifications and reminder scheduling |
| US-13 | Offline mode (`is_synced` flag) + sync endpoints |
| US-14 | Badge system (7 badges, auto-awarded) |
| US-15 | Docker + docker-compose (PostgreSQL 15 + gunicorn) |
| US-16 | Full test suite: 95 tests, ≥80% coverage |
| US-17 | GitHub Actions CI/CD pipeline |

---

## 🐳 Docker Reference

### Development Stack

```bash
# Start Flask API + PostgreSQL (background)
docker compose up -d --build

# View live API logs
docker compose logs -f api

# Run database migrations
docker compose exec api flask --app run_api db upgrade

# Re-seed demo data
docker compose exec api flask --app run_api seed-db

# Stop and remove all containers + volumes
docker compose down -v
```

### Service URLs

| Service | URL | Credentials |
|---------|-----|-------------|
| Flask API | http://localhost:5000 | — |
| API Health | http://localhost:5000/api/health | — |
| PostgreSQL | localhost:5432 | `fittrack` / `fittrack_pass` |

### Test Environment (isolated PostgreSQL)

```bash
# Run all tests inside Docker against real PostgreSQL 15
docker compose -f docker-compose.test.yml up --abort-on-container-exit

# Clean up
docker compose -f docker-compose.test.yml down -v
```

---

## 🔧 Environment Variables

Copy `.env.example` to `.env` and configure:

```env
# Flask
FLASK_ENV=development
SECRET_KEY=your-secret-key
JWT_SECRET_KEY=your-jwt-secret

# PostgreSQL (used by Flask API and Docker)
DATABASE_URL=postgresql://fittrack:fittrack_pass@localhost:5432/fittrack_dev
POSTGRES_USER=fittrack
POSTGRES_PASSWORD=fittrack_pass
POSTGRES_DB=fittrack_dev

# External Nutrition API — leave blank to use built-in fallback
# Free key at: https://developer.edamam.com/
NUTRITION_APP_ID=
NUTRITION_API_KEY=
```

---

## 📦 Full Requirements

### Desktop Client (`requirements.txt`)
```
PyQt6 >= 6.4.0
PyQt6-Qt6 >= 6.4.0
PyQt6-sip >= 13.4.0
SQLAlchemy >= 2.0.0
requests >= 2.31.0
pytest >= 7.4.0
pytest-cov >= 4.1.0
```

### Flask API (`requirements-api.txt`)
```
Flask == 3.0.0
Flask-SQLAlchemy == 3.1.1
Flask-JWT-Extended == 4.6.0
Flask-Cors == 4.0.0
Flask-Migrate == 4.0.5
psycopg2-binary == 2.9.9
SQLAlchemy == 2.0.23
requests == 2.31.0
requests-cache == 1.1.1
gunicorn == 21.2.0
python-dotenv == 1.0.0
```

### Testing (`requirements-test.txt`)
```
pytest == 7.4.3
pytest-cov == 4.1.0
pytest-flask == 1.3.0
flake8 == 7.0.0
responses == 0.24.1
```

---

## ✅ Assessment 3 Checklist

| Requirement | Status |
|-------------|--------|
| User registration / login | ✅ |
| Create and manage fitness profiles | ✅ |
| Set personal fitness goals | ✅ |
| Log workouts with exercises | ✅ |
| Record meal entries | ✅ |
| Update body measurements | ✅ |
| Calculate calorie totals (Mifflin-St Jeor) | ✅ |
| Generate weekly progress summaries | ✅ |
| Receive reminders for workouts and meals | ✅ |
| Coach dashboard with search/filter/export | ✅ |
| Offline mode with sync on reconnect | ✅ |
| External Nutrition API adapter + cache | ✅ |
| Flask REST API (all CRUD endpoints) | ✅ |
| PostgreSQL 15 database | ✅ |
| Docker + docker-compose deployment | ✅ |
| Flask-Migrate (Alembic) schema management | ✅ |
| PyQt6 desktop UI (all screens) | ✅ |
| Unit tests ≥ 80% coverage | ✅ (95 total tests) |
| Integration tests (POST /workouts, GET /progress) | ✅ |
| Acceptance tests (offline sync, coach export) | ✅ |
| Expected results table in test appendix | ✅ |
| GitHub Actions CI pipeline | ✅ (4 jobs) |
| Badge / reward system | ✅ (7 badges) |
| Use-case / sequence / class UML diagrams | See report |
| Layered + Ports-and-Adapters architecture | ✅ |
| Two 2-week Scrum sprints with backlog | ✅ |

---

*FitTrack Pro — MCS504 Assessment 3, B2 2026 | HealthHub Platform*