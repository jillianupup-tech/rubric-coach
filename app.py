"""Rubric Coach — web app for Render (EDUC 6192 Course Project, Zijia Luo).

Same grading workflow as the Rubric_Coach_V3 notebook. API requests happen only on
"Organize rubric" and "Grade all answers". Settings come from environment variables:
  OPENAI_API_KEY        required, set as a secret in Render
  ACCESS_CODE           optional; if set, users must enter it before using the API
  DAILY_REQUEST_LIMIT   optional, default 200 API requests per day
"""
import os, sys, csv, json, hmac, tempfile
from datetime import date
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import gradio as gr
from openai import OpenAI

from grading_core import *          # noqa: F401,F403  (grading logic)
from examples import EXAMPLES, RUBRIC_FORMAT_HELP
from file_reader import read_document, SUPPORTED_TYPES

ACCESS_CODE = os.environ.get("ACCESS_CODE", "").strip()
DAILY_REQUEST_LIMIT = int(os.environ.get("DAILY_REQUEST_LIMIT", "200"))
MAX_BATCH = 40            # answers per "Grade all answers" click
PARALLEL_REQUESTS = 4
_web_lock = Lock()
_usage = {"day": date.today().isoformat(), "count": 0}


def _code_ok(code):
    if not ACCESS_CODE:
        return True
    return isinstance(code, str) and hmac.compare_digest(code.strip(), ACCESS_CODE)


CODE_MESSAGE = "Enter the access code at the top of the page (ask the presenter). No API call made."


def _log(record):
    """Write each run to the Render logs (no prompt, no key) as evaluation evidence."""
    fields = ("run_id", "timestamp_utc", "version", "model", "api_called",
              "status", "response_id", "api_status", "usage", "error_type")
    safe = {k: record[k] for k in fields if k in record}
    print("RUBRIC_COACH_RECORD " + json.dumps(safe, ensure_ascii=False, default=str), flush=True)

EVIDENCE_LABELS = {"FOUND": "✓ found in answer", "NOT_FOUND": "⚠ not in answer",
                   "NO_QUOTE": "no quote", "MISSING": "⚠ missing", "TOO_LONG": "⚠ over 30 words"}
STATUS_LABELS = {"NO_AUTOMATIC_REVIEW_FLAGS": "Checks passed", "REVIEW_REQUIRED": "Teacher review required",
                 "INPUT_REQUIRED": "Not graded: input problem", "API_ERROR": "Not graded: API error",
                 "API_OUTPUT_INCOMPLETE": "Not graded: incomplete response", "FILE_ERROR": "Not graded: file problem"}

EXAMPLE_CHOICES = {}
for _task_name, _ex in EXAMPLES.items():
    EXAMPLE_CHOICES[f"{_task_name} — all sample answers"] = (_task_name, None)


def _reserve(n):
    with _web_lock:
        today = date.today().isoformat()
        if _usage["day"] != today:
            _usage.update(day=today, count=0)
        if _usage["count"] + n > DAILY_REQUEST_LIMIT:
            return False
        _usage["count"] += n
        return True


def _client():
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise ValueError("Missing key")
    return OpenAI(api_key=key, timeout=90.0, max_retries=0)


# ---------- Step 1 and 2: task and rubric ----------
def load_task_file(path, current):
    if not path:
        return current, "Ready."
    doc = read_document(path)
    if doc["error"]:
        return current, f"{doc['name']}: {doc['error']}"
    return doc["text"], f"Loaded the task from {doc['name']}."


def load_rubric_file(path, current):
    if not path:
        return current, "Ready."
    doc = read_document(path)
    if doc["error"]:
        return current, f"{doc['name']}: {doc['error']}"
    return doc["text"], f"Loaded your rubric from {doc['name']}. Click Organize rubric to convert it."


def organize_click(raw_rubric, task, current_structured, code):
    if not isinstance(raw_rubric, str) or not raw_rubric.strip():
        return current_structured, "Paste or upload your rubric first. No API call made.", []
    if parse_rubric(raw_rubric)["criteria"] and not parse_rubric(raw_rubric)["errors"]:
        status, rows = preview_rubric(raw_rubric)
        return raw_rubric, "Your rubric is already in the required format. " + status, rows
    identifiers = privacy_issues(raw_rubric) + privacy_issues(task)
    if identifiers:
        return current_structured, " | ".join(identifiers) + " No API call made.", []
    preserved = organize_maximum_only(raw_rubric)
    if preserved is not None:
        status, rows = preview_rubric(preserved)
        return preserved, "No scoring descriptions were invented. Add descriptors and resolve TEACHER CHECK before grading. " + status, rows
    if not _code_ok(code):
        return current_structured, CODE_MESSAGE, []
    if not _reserve(1):
        return current_structured, "The app has reached today's request limit. Please try again tomorrow.", []
    try:
        client = _client()
    except Exception:
        return current_structured, "The app is not configured yet (missing API key). Please tell the presenter.", []
    try:
        rec = organize_rubric(raw_rubric, task, client)
    finally:
        client.close()
    if not rec["rubric_text"]:
        return current_structured, "Could not organize the rubric: " + " | ".join(rec["issues"]), []
    status, rows = preview_rubric(rec["rubric_text"])
    note = (" Please check: " + " | ".join(rec["issues"])) if rec["issues"] else ""
    return (rec["rubric_text"], "Organized. Read it carefully and edit anything that is wrong before grading."
            + note + " " + status, rows)


def preview_rubric(rubric_text):
    rubric = parse_rubric(rubric_text)
    rows = [[c["name"], fmt_allowed(c["allowed"]), c["max"]] for c in rubric["criteria"] if c["allowed"]]
    if rubric["errors"]:
        return "Please fix the rubric: " + " | ".join(rubric["errors"]), rows
    total = sum(c["max"] for c in rubric["criteria"])
    return f"Rubric OK: {len(rubric['criteria'])} criteria, maximum total {total:g} points.", rows


# ---------- Step 3: answers ----------
def load_example(choice, task, raw_rubric, rubric_text, files, pasted):
    if choice not in EXAMPLE_CHOICES:
        return task, raw_rubric, rubric_text, files, pasted
    task_name, _ = EXAMPLE_CHOICES[choice]
    ex = EXAMPLES[task_name]
    folder = tempfile.mkdtemp(prefix="examples_")
    paths = []
    for answer_name, text in ex["answers"].items():
        p = os.path.join(folder, answer_name.replace(" ", "_") + ".txt")
        with open(p, "w", encoding="utf-8") as f:
            f.write(text)
        paths.append(p)
    return ex["task"], ex["rubric"], ex["rubric"], paths, ""


def _collect_answers(files, pasted):
    items = []
    for path in files or []:
        doc = read_document(path)
        items.append(doc)
    if isinstance(pasted, str) and pasted.strip():
        items.append({"name": "Pasted answer", "text": pasted.strip(), "error": None})
    # make names unique
    seen = set()
    for it in items:
        base = it["name"]
        name, suffix = base, 2
        while name in seen:
            name = f"{base} ({suffix})"
            suffix += 1
        it["name"] = name
        seen.add(name)
        identifiers = privacy_issues(base)
        if identifiers and not it["error"]:
            it["error"] = identifiers[0]
    return items


# ---------- Grading ----------
def _detail(entry, criteria):
    rec = entry.get("record") or {}
    parsed = rec.get("parsed_result") if isinstance(rec.get("parsed_result"), dict) else {}
    scores = parsed.get("scores") if isinstance(parsed.get("scores"), dict) else {}
    feedback = parsed.get("feedback") if isinstance(parsed.get("feedback"), dict) else {}
    evidence = parsed.get("evidence") if isinstance(parsed.get("evidence"), dict) else {}
    ev_check = rec.get("evidence_check") or {}
    rows = [[c["name"], str(scores.get(c["id"], "—")), c["max"], EVIDENCE_LABELS.get(ev_check.get(c["id"]), "—")]
            for c in criteria] if scores else []
    blocks = []
    for c in criteria:
        if not feedback:
            break
        text = f"{c['name']}\n{feedback.get(c['id'], 'No feedback returned.')}"
        q = evidence.get(c["id"])
        if isinstance(q, str) and q.strip():
            text += f"\nStudent's words: \"{q.strip()}\" [{EVIDENCE_LABELS.get(ev_check.get(c['id']), 'not checked')}]"
        blocks.append(text)
    details = "\n\n".join(blocks)
    issues = rec.get("issues") or ([entry["error"]] if entry.get("error") else [])
    if issues:
        details += "\n\nChecks: " + " | ".join(issues)
    if rec.get("review_reason"):
        details += "\n\nReview note: " + rec["review_reason"]
    shown = {k: v for k, v in rec.items() if k not in ("prompt", "task", "rubric_text")}
    return rows, details.strip(), shown


def _write_csv(results, criteria):
    path = os.path.join(tempfile.mkdtemp(prefix="results_"), "rubric_coach_results.csv")
    def safe_cell(value):
        if isinstance(value, str) and value.lstrip(" \t\r\n").startswith(("=", "+", "-", "@")):
            return "'" + value
        return value
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        class SafeWriter:
            def __init__(self, stream):
                self.writer = csv.writer(stream)
            def writerow(self, row):
                self.writer.writerow([safe_cell(cell) for cell in row])
        w = SafeWriter(f)
        w.writerow(["Answer file", "Status", "Suggested total", "Maximum"]
                   + [f"{c['name']} score" for c in criteria]
                   + [f"{c['name']} evidence check" for c in criteria]
                   + [f"{c['name']} feedback" for c in criteria] + ["Automatic checks", "Review note"])
        for e in results:
            rec = e.get("record") or {}
            parsed = rec.get("parsed_result") if isinstance(rec.get("parsed_result"), dict) else {}
            scores = parsed.get("scores") if isinstance(parsed.get("scores"), dict) else {}
            fb = parsed.get("feedback") if isinstance(parsed.get("feedback"), dict) else {}
            ev = rec.get("evidence_check") or {}
            total = rec.get("total")
            w.writerow([e["name"], STATUS_LABELS.get(e["status"], e["status"]),
                        "" if total is None else f"{total:g}", "" if not criteria else f"{sum(c['max'] for c in criteria):g}"]
                       + [scores.get(c["id"], "") for c in criteria]
                       + [EVIDENCE_LABELS.get(ev.get(c["id"]), "") for c in criteria]
                       + [fb.get(c["id"], "") for c in criteria]
                       + [" | ".join(rec.get("issues") or ([e["error"]] if e.get("error") else [])),
                          rec.get("review_reason") or ""])
    return path


def grade_all(task, rubric_text, files, pasted, code, progress=gr.Progress()):
    empty = ([], gr.Dropdown(choices=[], value=None), [], "", {}, None, {"results": [], "criteria": []})
    setup = validate_inputs(task, rubric_text, "placeholder answer")
    if not setup["valid"]:
        return ("Please fix before grading (no API call made): " + " | ".join(setup["issues"]),) + empty
    criteria = setup["rubric"]["criteria"]
    items = _collect_answers(files, pasted)
    if not items:
        return ("Upload at least one student answer file or paste an answer. No API call made.",) + empty
    if len(items) > MAX_BATCH:
        return (f"Please grade at most {MAX_BATCH} answers at a time (you added {len(items)}).",) + empty
    gradable = [it for it in items if not it["error"]]
    if gradable and not _code_ok(code):
        return (CODE_MESSAGE,) + empty
    if gradable and not _reserve(len(gradable)):
        return ("Grading these answers would exceed the app's daily request limit. "
                "Please grade fewer answers or try again tomorrow.",) + empty
    client = None
    if gradable:
        try:
            client = _client()
        except Exception:
            return ("The app is not configured yet (missing API key). Please tell the presenter.",) + empty

    results = {it["name"]: {"name": it["name"], "status": "FILE_ERROR", "error": it["error"], "record": None}
               for it in items if it["error"]}
    try:
        if gradable:
            progress((0, len(gradable)), desc="Grading answers")
            with ThreadPoolExecutor(max_workers=PARALLEL_REQUESTS) as pool:
                futures = {pool.submit(grade_answer, task.strip(), rubric_text, it["text"], client, it["name"]): it
                           for it in gradable}
                for done, fut in enumerate(as_completed(futures), start=1):
                    it = futures[fut]
                    try:
                        rec = fut.result()
                    except Exception as error:
                        rec = {"status": "API_ERROR", "issues": [f"Unexpected error ({type(error).__name__})."]}
                    _log(rec)
                    results[it["name"]] = {"name": it["name"], "status": rec["status"], "error": None, "record": rec}
                    progress((done, len(gradable)), desc="Grading answers")
    finally:
        if client is not None:
            client.close()

    ordered = [results[it["name"]] for it in items]
    max_total = sum(c["max"] for c in criteria)
    summary = []
    for e in ordered:
        rec = e.get("record") or {}
        total = rec.get("total")
        flags = len(rec.get("issues") or ([e["error"]] if e.get("error") else []))
        summary.append([e["name"], "—" if total is None else f"{total:g}", max_total,
                        STATUS_LABELS.get(e["status"], e["status"]), flags])
    n_ok = sum(e["status"] == "NO_AUTOMATIC_REVIEW_FLAGS" for e in ordered)
    n_review = sum(e["status"] == "REVIEW_REQUIRED" for e in ordered)
    n_fail = len(ordered) - n_ok - n_review
    status = (f"Graded {len(ordered)} answer(s): {n_ok} passed the automatic checks, {n_review} need teacher review, "
              f"{n_fail} could not be graded. All scores are suggestions; a teacher must review them.")
    names = [e["name"] for e in ordered]
    rows, details, shown = _detail(ordered[0], criteria)
    csv_path = _write_csv(ordered, criteria)
    state = {"results": ordered, "criteria": criteria}
    return (status, summary, gr.Dropdown(choices=names, value=names[0]), rows, details, shown, csv_path, state)


def show_student(name, state):
    for e in (state or {}).get("results", []):
        if e["name"] == name:
            return _detail(e, state["criteria"])
    return [], "", {}


# ---------- Layout ----------
with gr.Blocks(title="Rubric Coach | Assessment Assistant") as assessment_demo:
    results_state = gr.State({"results": [], "criteria": []})
    gr.Markdown("# Rubric Coach\n### Rubric-based feedback for any short-answer task\n"
                "Add your task and rubric, upload your students' answers, and get suggested scores, feedback, and the "
                "student's own words behind each score. **Scores are suggestions; the teacher makes the final decision.** "
                "Use fictional or de-identified work only.")
    with gr.Row():
        code_box = gr.Textbox(label="Access code", type="password", visible=bool(ACCESS_CODE), scale=1)
        example_pick = gr.Dropdown(choices=list(EXAMPLE_CHOICES), label="Try an example (optional)", value=None, scale=2)
    status_box = gr.Textbox(label="Status", value="Ready when you are.", interactive=False)

    gr.Markdown("## 1. Task or question")
    with gr.Row():
        task_box = gr.Textbox(label="Task", lines=6, max_lines=14, scale=3,
                              placeholder="Paste the question or assignment, or upload a file →")
        task_file = gr.File(label="Upload task (.docx, .pdf, .txt)", file_types=SUPPORTED_TYPES, type="filepath", scale=1)

    gr.Markdown("## 2. Rubric")
    with gr.Row():
        with gr.Column():
            raw_rubric_box = gr.Textbox(label="Your rubric, in any format", lines=10, max_lines=24,
                                        placeholder="Paste your rubric as you normally write it, or upload a file below.")
            rubric_file = gr.File(label="Upload rubric (.docx, .pdf, .txt)", file_types=SUPPORTED_TYPES, type="filepath")
            organize_button = gr.Button("Organize rubric (1 API request)")
        with gr.Column():
            rubric_box = gr.Textbox(label="Rubric used for grading — check and edit before grading", lines=14, max_lines=28,
                                    placeholder="## Criterion name | 0, 1, 2\nWhat earns each score…")
            check_button = gr.Button("Check rubric (free, no API call)")
            with gr.Accordion("Rubric format", open=False):
                gr.Markdown(RUBRIC_FORMAT_HELP)
            rubric_table = gr.Dataframe(headers=["Criterion", "Allowed scores", "Maximum"],
                                        datatype=["str", "str", "number"], interactive=False)

    gr.Markdown("## 3. Student answers")
    with gr.Row():
        answer_files = gr.File(label=f"Upload answers — one student per file (up to {MAX_BATCH}; .docx, .pdf, .txt)",
                               file_count="multiple", file_types=SUPPORTED_TYPES, type="filepath")
        pasted_answer = gr.Textbox(label="…or paste a single answer", lines=6, max_lines=14)
    grade_button = gr.Button("Grade all answers", variant="primary")
    gr.Markdown("Each answer is one API request. Grading several answers can take a minute or more.")

    gr.Markdown("## 4. Results")
    summary_table = gr.Dataframe(headers=["Answer file", "Suggested total", "Maximum", "Status", "Flags"],
                                 datatype=["str", "str", "number", "str", "number"], interactive=False)
    download = gr.File(label="Download all results (CSV, opens in Excel)", interactive=False)
    student_pick = gr.Dropdown(choices=[], label="View one student's feedback", value=None)
    with gr.Row():
        score_table = gr.Dataframe(headers=["Criterion", "AI draft score (unapproved)", "Maximum", "Evidence check"],
                                   datatype=["str", "str", "number", "str"], interactive=False)
        feedback_box = gr.Textbox(label="Feedback and evidence", lines=16, interactive=False)
    with gr.Accordion("Inspect this response (run record)", open=False):
        evidence_box = gr.JSON(label="Run record — contains no API key")
    gr.Markdown("Educational prototype · Zijia Luo · EDUC 6192 Course Project\n\n"
                "Automatic checks confirm the response format, that every score is an allowed value for its criterion, "
                "and that each quoted piece of evidence really appears in the student's answer. "
                "They do not prove the assessment is correct. A flagged total is withheld. "
                "Privacy screening catches common identifiers only; remove all identifying information yourself.")

    example_pick.change(load_example, inputs=[example_pick, task_box, raw_rubric_box, rubric_box, answer_files, pasted_answer],
                        outputs=[task_box, raw_rubric_box, rubric_box, answer_files, pasted_answer], api_name=False)
    task_file.upload(load_task_file, inputs=[task_file, task_box], outputs=[task_box, status_box], api_name=False)
    rubric_file.upload(load_rubric_file, inputs=[rubric_file, raw_rubric_box], outputs=[raw_rubric_box, status_box], api_name=False)
    organize_button.click(organize_click, inputs=[raw_rubric_box, task_box, rubric_box, code_box],
                          outputs=[rubric_box, status_box, rubric_table], concurrency_limit=1, api_name=False)
    check_button.click(preview_rubric, inputs=rubric_box, outputs=[status_box, rubric_table], api_name=False)
    grade_button.click(grade_all, inputs=[task_box, rubric_box, answer_files, pasted_answer, code_box],
                       outputs=[status_box, summary_table, student_pick, score_table, feedback_box, evidence_box,
                                download, results_state],
                       concurrency_limit=1, api_name=False)
    student_pick.change(show_student, inputs=[student_pick, results_state],
                        outputs=[score_table, feedback_box, evidence_box], api_name=False)
assessment_demo.queue(max_size=20)

if __name__ == "__main__":
    assessment_demo.launch(server_name="0.0.0.0", server_port=int(os.environ.get("PORT", "7860")), show_error=False)
