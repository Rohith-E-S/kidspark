# Project Specification: KidSpark — Child Aptitude & Interest Assessment Platform

## 1. Project Overview
Build a complete, production-ready, trial-run-ready Django web application titled **"KidSpark"** that assesses a child's cognitive aptitude and areas of interest[cite: 1]. The platform must allow Parents/Educators to create child profiles, let children take an interactive, gamified two-part assessment (Cognitive Aptitude + Interest Inventory), calculate multi-dimensional scores, and generate a visual dashboard with Chart.js radar/bar charts, personalized learning paths, and a printable report card.

## 2. Tech Stack & Dependencies
- **Backend:** Python 3.11+, Django 5.x (Monolithic MVT architecture for clean university evaluation)
- **Database:** SQLite3 (`db.sqlite3` pre-seeded and ready for immediate local execution)
- **Frontend:** Django Templates + Tailwind CSS (via CDN for zero-build setup) + Alpine.js (for interactive quiz state/timers) + HTMX (for smooth question transitions without full page reloads)
- **Data Visualization:** Chart.js (Radar chart for Aptitude, Horizontal Bar chart for Interests)
- **Icons & Fonts:** Lucide Icons / FontAwesome CDN, Google Fonts ('Plus Jakarta Sans' & 'Fredoka' for child-friendly UI)

---

## 3. Core Assessment Domains
The system evaluates two main pillars across 8 specific dimensions[cite: 1]:

### Pillar A: Cognitive Aptitude (Objective Scored Questions - Right/Wrong + Weighted Difficulty)
1. **Logical & Mathematical (`LOGICAL`)**: Pattern recognition, number puzzles, deductive reasoning.
2. **Verbal & Linguistic (`VERBAL`)**: Vocabulary, reading comprehension, word associations.
3. **Spatial & Visual (`SPATIAL`)**: Mental rotation, shape matching, visual memory.
4. **Critical & Analytical (`CRITICAL`)**: Cause-and-effect, everyday problem solving.

### Pillar B: Areas of Interest (Preference/Likert Questions - Scored by Affinity Weight)
5. **STEM & Discovery (`STEM`)**: Science experiments, coding, robotics, how things work.
6. **Arts & Creative Expression (`ARTS`)**: Drawing, music, storytelling, design.
7. **Nature & Outdoors (`NATURE`)**: Animals, environment, space, physical exploration.
8. **Social & Leadership (`SOCIAL`)**: Teamwork, helping others, organizing games, communication.

---

## 4. Project Directory Structure
Initialize a Django project named `aptitude_platform` in the current directory with the following modular app structure:

    kidspark/
    ├── manage.py
    ├── requirements.txt
    ├── aptitude_platform/          # Project config (settings, urls, wsgi)
    ├── accounts/                   # Parent/Teacher Auth & Child Profile Management
    ├── assessments/                # Questions, Options, Quiz Engine, Seeding Command
    ├── analytics/                  # Scoring Engine, Career/Hobby Recommendations, Report Views
    ├── templates/
    │   ├── base.html               # Master layout with navbar, toast alerts, Tailwind/HTMX/Chart.js CDNs
    │   ├── home.html               # Landing page with "Quick Demo Login" button for evaluators
    │   ├── accounts/
    │   │   ├── login.html
    │   │   ├── register.html
    │   │   ├── dashboard.html      # Parent overview of all children & past assessments
    │   │   └── child_form.html     # Add/Edit Child Profile
    │   ├── assessments/
    │   │   ├── select_test.html    # Choose child & start assessment
    │   │   ├── quiz_play.html      # Interactive gamified quiz interface with progress bar
    │   │   └── partials/
    │   │       └── question_card.html # HTMX partial for seamless question switching
    │   └── analytics/
    │       └── report_detail.html  # Comprehensive visual report with Radar/Bar charts & print CSS
    └── static/
        └── css/custom.css          # Print media queries for PDF report export

---

## 5. Database Schema (`models.py`)

### App 1: `accounts`
1. **`ChildProfile`**
   - `parent`: ForeignKey to `auth.User` (on_delete=CASCADE, related_name='children')
   - `name`: CharField(max_length=100)
   - `age`: PositiveIntegerField (choices/range: 6 to 16)
   - `age_group`: CharField(max_length=10, choices=[('JUNIOR', '6-9 Years'), ('MIDDLE', '10-12 Years'), ('SENIOR', '13-16 Years')]) — auto-computed on `save()` based on `age` (6-9 -> JUNIOR, 10-12 -> MIDDLE, 13-16 -> SENIOR).
   - `grade`: CharField(max_length=50)
   - `avatar_color`: CharField(max_length=20, default='indigo')
   - `created_at`: DateTimeField(auto_now_add=True)

### App 2: `assessments`
1. **`Category`**
   - `code`: CharField(max_length=20, unique=True) # LOGICAL, VERBAL, SPATIAL, CRITICAL, STEM, ARTS, NATURE, SOCIAL
   - `name`: CharField(max_length=100)
   - `pillar`: CharField(max_length=20, choices=[('APTITUDE', 'Cognitive Aptitude'), ('INTEREST', 'Area of Interest')])
   - `description`: TextField()
   - `icon_name`: CharField(max_length=50)

2. **`Question`**
   - `category`: ForeignKey to `Category` (on_delete=CASCADE, related_name='questions')
   - `age_group`: CharField(max_length=10, choices=[('JUNIOR', '6-9 Years'), ('MIDDLE', '10-12 Years'), ('SENIOR', '13-16 Years'), ('ALL', 'All Ages')], default='ALL')
   - `question_type`: CharField(max_length=20, choices=[('OBJECTIVE', 'Aptitude Multiple Choice'), ('PREFERENCE', 'Interest Scenario')])
   - `text`: TextField()
   - `visual_hint`: CharField(max_length=255, blank=True, help_text="Short puzzle or scenario cue printed above the question")
   - `difficulty_weight`: IntegerField(default=1) # 1=Easy, 2=Medium, 3=Hard
   - `order`: PositiveIntegerField(default=0)

3. **`Choice`**
   - `question`: ForeignKey to `Question` (on_delete=CASCADE, related_name='choices')
   - `text`: CharField(max_length=255)
   - `icon_name`: CharField(max_length=40, blank=True) # Lucide icon name, rendered client-side
   - `is_correct`: BooleanField(default=False) # Used if question_type == OBJECTIVE
   - `score_weight`: IntegerField(default=0) # For OBJECTIVE: 10 if correct else 0. For PREFERENCE: 10 (Love it), 5 (Sometimes), 0 (Not for me)

4. **`AssessmentSession`**
   - `child`: ForeignKey to `ChildProfile` (on_delete=CASCADE, related_name='sessions')
   - `started_at`: DateTimeField(auto_now_add=True)
   - `completed_at`: DateTimeField(null=True, blank=True)
   - `is_completed`: BooleanField(default=False)
   - `current_question_index`: PositiveIntegerField(default=0)

5. **`SessionResponse`**
   - `session`: ForeignKey to `AssessmentSession` (on_delete=CASCADE, related_name='responses')
   - `question`: ForeignKey to `Question` (on_delete=CASCADE)
   - `selected_choice`: ForeignKey to `Choice` (on_delete=CASCADE)
   - `time_taken_seconds`: PositiveIntegerField(default=5)
   - `answered_at`: DateTimeField(auto_now_add=True)
   - Meta Constraint: `unique_together = ('session', 'question')`

### App 3: `analytics`
1. **`AssessmentResult`**
   - `session`: OneToOneField to `AssessmentSession` (on_delete=CASCADE, related_name='result')
   - `aptitude_scores`: JSONField(default=dict) # e.g., {"LOGICAL": 85, "VERBAL": 70, "SPATIAL": 90, "CRITICAL": 75}
   - `interest_scores`: JSONField(default=dict) # e.g., {"STEM": 95, "ARTS": 60, "NATURE": 50, "SOCIAL": 80}
   - `overall_aptitude_percentage`: FloatField(default=0.0)
   - `dominant_aptitude`: ForeignKey to `assessments.Category` (null=True, on_delete=SET_NULL, related_name='+')
   - `dominant_interest`: ForeignKey to `assessments.Category` (null=True, on_delete=SET_NULL, related_name='+')
   - `persona_title`: CharField(max_length=100)
   - `persona_summary`: TextField()
   - `recommended_activities`: JSONField(default=list)
   - `recommended_future_domains`: JSONField(default=list)
   - `generated_at`: DateTimeField(auto_now_add=True)

---

## 6. Scoring & Recommendation Engine (`analytics/services.py`)
Implement a deterministic, rule-based evaluation service `generate_assessment_result(session)`:
1. **Normalized Percentage Calculation:**
   - Group all `SessionResponse` items by `question.category`.
   - For each category, compute `earned_points = sum(r.selected_choice.score_weight * r.question.difficulty_weight)` and `max_possible_points = sum(10 * r.question.difficulty_weight)`.
   - Normalize each category score to a `0-100` integer scale (`round((earned_points / max_possible_points) * 100)`).
   - Calculate `overall_aptitude_percentage` as the average of the 4 Aptitude category scores.
2. **Dominant Trait Detection:**
   - Identify `dominant_aptitude` (highest score among `LOGICAL`, `VERBAL`, `SPATIAL`, `CRITICAL`).
   - Identify `dominant_interest` (highest score among `STEM`, `ARTS`, `NATURE`, `SOCIAL`).
3. **Persona & Actionable Recommendations Matrix:**
   - Create a complete 16-combination lookup dictionary mapping `(dominant_aptitude.code, dominant_interest.code)` to:
     - **`persona_title`**: e.g., `('LOGICAL', 'STEM') -> "The Young Architect & Code Explorer"`, `('VERBAL', 'ARTS') -> "The Imaginative Storyteller"`, `('SPATIAL', 'ARTS') -> "The Visual Designer"`, `('CRITICAL', 'SOCIAL') -> "The Empathetic Leader"`.
     - **`persona_summary`**: A warm, encouraging 3-sentence paragraph explaining the child's cognitive strength and how it pairs with their primary interest.
     - **`recommended_activities`**: 4 concrete weekly activities tailored to the child's age group (e.g., Scratch/Python game building, LEGO robotics, debate club, nature journaling, chess puzzles).
     - **`recommended_future_domains`**: 4 broad career/academic clusters (e.g., Robotics & AI, Environmental Science, Digital Media & Architecture, Behavioral Psychology & Law).

---

## 7. Key User Flows, Views & Templates

1. **Landing Page (`/`)**:
   - Engaging hero section explaining how the 2-pillar assessment works.
   - **"Instant Demo Login" Button (`POST /accounts/demo-login/`)**: Automatically logs in as a pre-seeded demo parent (`demo_parent` / `demo1234`) and redirects to `/dashboard/` so university evaluators can test the entire app in one click.
   - Standard Login (`/accounts/login/`), Register (`/accounts/register/`), and Logout (`/accounts/logout/`) views.
2. **Parent Dashboard (`/dashboard/`)**:
   - Displays summary stats cards (Total Children, Assessments Completed, Top Discovered Strengths).
   - Lists all `ChildProfile` cards with their age badge, grade, number of completed tests, and quick action buttons: **"Start New Assessment"**, **"Resume Test"** (if an incomplete session exists), and **"View Latest Report"**.
   - Button and form to add a new child profile (`/children/add/`) or edit/delete an existing child profile.
3. **Interactive Quiz Engine (`/assessments/start/<child_id>/` & `/assessments/session/<session_id>/`)**:
   - Creates a new `AssessmentSession` or resumes an incomplete one.
   - Kid-friendly UI: Large clickable option cards with Lucide icons/visual hints, animated progress bar (`Question X of 24`), pillar badge ("Part 1: Brain Puzzles" vs "Part 2: What Do You Love?"), and silent time tracking via hidden input.
   - Supports both standard POST and HTMX partial swaps (`partials/question_card.html`).
   - Upon answering the final question, automatically marks `session.is_completed = True`, runs `generate_assessment_result(session)`, and redirects to `/analytics/report/<session_id>/`.
4. **Comprehensive Report Card (`/analytics/report/<session_id>/`)**:
   - **Header Banner**: Child's details, age group badge, completion date, Persona Badge (`persona_title`), and `persona_summary`.
   - **Dual Charts (Chart.js)**:
     - Left: **Radar Chart** mapping the 4 Cognitive Aptitude dimensions (`0-100`).
     - Right: **Horizontal Bar Chart** mapping the 4 Interest dimensions (`0-100`) with distinct colors.
   - **Dimension Breakdown Cards**: Individual progress bars and status badges for all 8 categories (`Strong >= 75%`, `Developing 45-74%`, `Emerging < 45%`).
   - **Personalized Roadmap**: 2 columns showing "Recommended Weekly Activities" and "Future Academic & Career Pathways".
   - **Question-by-Question Review Accordion**: Expandable section showing which objective questions the child got right/wrong and their preference selections.
   - **Print / Save as PDF Button**: Triggers `window.print()` with clean `@media print` CSS rules that hide navigation buttons and format the report neatly.

---

## 8. Database Seeding Command (`python manage.py seed_data`)
Create an idempotent custom management command `assessments/management/commands/seed_data.py` that populates:
1. **All 8 Categories** (4 Aptitude: `LOGICAL`, `VERBAL`, `SPATIAL`, `CRITICAL`; 4 Interest: `STEM`, `ARTS`, `NATURE`, `SOCIAL`) with rich descriptions and icons.
2. **24 High-Quality Questions** (3 questions per category = 12 Objective Aptitude questions with visual pattern hints and 4 choices each + 12 Interest Scenario questions with 3 weighted preference choices each: 10 pts, 5 pts, 0 pts).
3. **Demo Parent Account** (`username: demo_parent`, `password: demo1234`, `email: parent@kidspark.edu`) and a Superuser (`username: admin`, `password: admin1234`).
4. **2 Pre-Seeded Child Profiles under `demo_parent`**:
   - *Aarav (Age 11, Middle, 6th Grade)* — with a **fully completed `AssessmentSession` (all 24 `SessionResponse` records) and generated `AssessmentResult`** so the evaluator can view a populated analytics report immediately upon launch.
   - *Diya (Age 8, Junior, 3rd Grade)* — with 0 completed sessions, ready to start a live trial quiz during the demonstration.

---

## 9. Execution & Verification Steps for Claude Code
Execute the following steps sequentially without stopping:
1. Check Python environment, install `django` if not installed, and generate `requirements.txt`.
2. Scaffold the Django project `aptitude_platform` and apps `accounts`, `assessments`, `analytics`.
3. Implement all models and register them in `admin.py` with `TabularInline` for `Choice` inside `QuestionAdmin`.
4. Implement `analytics/services.py`, all views, forms, URLs, templates, and static CSS.
5. Build the `seed_data.py` management command.
6. Run `python manage.py makemigrations`, `python manage.py migrate`, and `python manage.py seed_data`.
7. Write and run automated Django tests (`python manage.py test`) verifying:
   - Home page and Instant Demo Login (`POST /accounts/demo-login/`) work properly.
   - Creating a child profile computes `age_group` accurately.
   - Starting a quiz session, submitting answers for all 24 questions, and generating `AssessmentResult` calculates normalized scores and persona recommendations without errors.
   - Report view (`/analytics/report/<session_id>/`) renders HTTP 200 and contains valid chart data.
