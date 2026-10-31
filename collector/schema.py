"""CSV schema (plan section 8). Unknown values stay blank, never guessed."""
import re

COLUMNS = ["job_id", "source", "title", "company", "location", "metro", "remote",
           "salary", "skills", "url", "description_snippet", "date_posted", "date_fetched"]
SNIPPET_LEN = 300


def _clean(value):
    return re.sub(r"\s+", " ", value or "").strip()


def snippet(text):
    text = _clean(text)
    if len(text) <= SNIPPET_LEN:
        return text
    return text[:SNIPPET_LEN].rsplit(" ", 1)[0] + "..."


def to_row(job, metro, skills, date_fetched):
    """Turn a collector job dict into one CSV row (all strings, one line each)."""
    row = {
        "job_id": job["job_id"],
        "source": job["source"],
        "title": job.get("title", ""),
        "company": job.get("company", ""),
        "location": job.get("location", ""),
        "metro": "" if job.get("remote") else metro,
        "remote": "true" if job.get("remote") else "false",
        "salary": job.get("salary", ""),
        "skills": "|".join(skills),
        "url": job.get("url", ""),
        "description_snippet": snippet(job.get("summary") or job.get("text", "")),
        "date_posted": job.get("date_posted", ""),
        "date_fetched": date_fetched,
    }
    return {k: _clean(v) for k, v in row.items()}
