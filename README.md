# Rubric Coach

Rubric-based feedback for any short-answer task. A teacher adds a task and rubric (pasted, or uploaded as Word / PDF / text), uploads students' answers (one file per student), and gets suggested scores, feedback, and the student's own words behind each score, plus a CSV export.

EDUC 6192 Course Project · Zijia Luo · built on Applied Assignment 3 (Variance Coach).

## Safeguards
- Inputs are checked before any API call (blank task, malformed rubric, unreadable or scanned files).
- The model must return structured JSON. Python rejects missing or non-allowed scores and withholds the total.
- Each score must quote the student's words; Python confirms each quote appears in the answer.
- All scores are suggestions for teacher review.

## Render settings
- Build command: `pip install -r requirements.txt`
- Start command: `python app.py`
- Environment variables:
  - `OPENAI_API_KEY` (required, keep secret)
  - `PYTHON_VERSION` = `3.12.8`
  - `ACCESS_CODE` (optional; users must enter it before the app calls the API)
  - `DAILY_REQUEST_LIMIT` (optional, default 200)

Each graded run is written to the service logs on a line starting with `RUBRIC_COACH_RECORD` (no prompt, no key).
Use fictional or de-identified student work only.
