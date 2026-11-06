"""Local Flask page that shows data/jobs.csv with filters (plan section 10).

Run:  flask --app app.app run
Dummy data:  JOBS_CSV=app/dummy_jobs.csv flask --app app.app run
"""
import csv
import io
import logging
import os
import time

import requests
from flask import Flask, render_template, request

from app import resume
from collector import skills

RAW_URL = "https://raw.githubusercontent.com/Sethcbs/Suited-Jobs/main/data/jobs.csv"
CACHE_SECONDS = 300
PLACES = ["Portland", "Seattle", "Remote"]

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = resume.MAX_BYTES
log = logging.getLogger(__name__)
_cache = {"source": None, "rows": None, "time": 0.0}


def _read(source):
    if source.startswith(("http://", "https://")):
        resp = requests.get(source, timeout=15)
        resp.raise_for_status()
        text = resp.text
    else:
        with open(source, encoding="utf-8") as f:
            text = f.read()
    return list(csv.DictReader(io.StringIO(text)))


def load_rows(source):
    """Rows from a URL or file, cached briefly. Falls back to the last good copy."""
    fresh = time.time() - _cache["time"] < CACHE_SECONDS
    if _cache["source"] == source and fresh:
        return _cache["rows"]
    try:
        rows = _read(source)
    except Exception as exc:
        if _cache["source"] == source and _cache["rows"] is not None:
            log.warning("Could not fetch %s (%s); using last copy", source, type(exc).__name__)
            return _cache["rows"]
        raise
    _cache.update(source=source, rows=rows, time=time.time())
    return rows


def filter_rows(rows, places=(), skill="", source=""):
    """places: any of Portland/Seattle/Remote (none = all). Newest first."""
    out = []
    for row in rows:
        place = "Remote" if row["remote"] == "true" else row["metro"]
        if places and place not in places:
            continue
        if skill and skill not in row["skills"].split("|"):
            continue
        if source and row["source"] != source:
            continue
        out.append(row)
    return sorted(out, key=lambda r: r["date_posted"], reverse=True)


@app.route("/")
def index():
    data_source = os.environ.get("JOBS_CSV", RAW_URL)
    error = ""
    try:
        rows = load_rows(data_source)
    except Exception as exc:
        rows, error = [], f"Could not load jobs ({type(exc).__name__})."
    places = [p for p in request.args.getlist("place") if p in PLACES]
    skill = request.args.get("skill", "")
    source = request.args.get("source", "")
    shown = filter_rows(rows, places, skill, source)
    return render_template(
        "index.html", rows=shown, total=len(rows), error=error, data_source=data_source,
        places=PLACES, chosen_places=places, skill=skill, source=source,
        all_skills=sorted({s for r in rows for s in r["skills"].split("|") if s}),
        all_sources=sorted({r["source"] for r in rows}),
    )


def _match_page(status=200, **context):
    defaults = {"error": "", "resume_text": "", "resume_skills": [], "chosen_places": []}
    return render_template("match.html", places=PLACES, **{**defaults, **context}), status


@app.errorhandler(413)
def too_large(_error):
    return _match_page(413, error="That file is too large. The limit is 5 MB.")


@app.route("/match", methods=["GET", "POST"])
def match():
    if request.method == "GET":
        return _match_page()
    places = [p for p in request.form.getlist("place") if p in PLACES]
    upload = request.files.get("resume")
    if not upload or not upload.filename:
        return _match_page(400, error="Please choose a PDF resume.", chosen_places=places)
    try:
        text = resume.extract_text(upload.read())
    except resume.ResumeError as exc:
        return _match_page(400, error=str(exc), chosen_places=places)
    return _match_page(resume_text=text, resume_skills=skills.find(text, skills.load()),
                       chosen_places=places)
