# KidSpark

A Django app that assesses a child's **cognitive aptitude** and **areas of interest**
across eight dimensions, then turns the result into a named persona, two charts, and a
concrete four-week learning plan.

Built for children aged 6–16, used by parents and educators.

---

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python manage.py migrate       # the shipped db.sqlite3 is already migrated
python manage.py seed_data     # idempotent: 8 categories, 24 questions, demo data
python manage.py runserver
```

Open <http://127.0.0.1:8000/> and press **Instant demo login**.

| Account    | Username      | Password     |
|------------|---------------|--------------|
| Demo parent| `demo_parent` | `demo1234`   |
| Superuser  | `admin`       | `admin1234`  |

The demo parent owns two children:

- **Aarav** (11, Middle) — a completed 24-question session, so the full report card is
  visible immediately.
- **Diya** (8, Junior) — no sessions, ready for a live trial quiz.

---

## What the assessment does

| Part | Questions | Scored by |
|------|-----------|-----------|
| 1 — Brain puzzles | 12 objective multiple-choice | right/wrong, weighted by difficulty (1–3) |
| 2 — What do you love? | 12 preference scenarios | affinity: 10 / 5 / 0 |

Eight dimensions, four per pillar:

- **Aptitude** — `LOGICAL`, `VERBAL`, `SPATIAL`, `CRITICAL`
- **Interest** — `STEM`, `ARTS`, `NATURE`, `SOCIAL`

Each dimension is normalised to 0–100:

```
score = round( sum(choice.score_weight * question.difficulty_weight)
             / sum(10          * question.difficulty_weight) * 100 )
```

`overall_aptitude_percentage` is the mean of the four aptitude scores. The highest
aptitude × highest interest pair selects one of **16 personas** from the recommendation
matrix in `analytics/services.py`, each carrying a summary, four age-appropriate weekly
activities, and four future pathways.

---

## Project layout

```
aptitude_platform/          settings, root urls
accounts/                   auth, ChildProfile (age_group auto-computed on save)
assessments/                Category, Question, Choice, AssessmentSession,
                            SessionResponse, quiz views, seed_data command
analytics/                  AssessmentResult, scoring engine, report views
templates/                  base + per-app templates (Tailwind/Alpine/HTMX/Chart.js via CDN)
static/css/custom.css       design layer + @media print rules
```

## Routes

| Path | Purpose |
|------|---------|
| `/` | Landing page + instant demo login |
| `/dashboard/` | Children, stats, start/resume/view report |
| `/children/add/`, `/children/<id>/edit/` | Child profiles |
| `/assessments/select/` | Pick a child |
| `/assessments/start/<child_id>/` | Create or resume a session |
| `/assessments/session/<id>/` | Quiz engine (POST + HTMX partials) |
| `/analytics/report/<id>/` | Report card (charts, roadmap, review, print) |
| `/analytics/reports/` | Every completed report |
| `/admin/` | Django admin |

## Tests

```bash
python manage.py test
```

40 tests covering demo login, `age_group` computation, the quiz flow (including the
HTMX path and cross-question choice rejection), score normalisation, the 16-persona
matrix, ownership isolation, and report rendering.

---

## Notes

Results are guidance for parents and educators, not a clinical diagnosis.