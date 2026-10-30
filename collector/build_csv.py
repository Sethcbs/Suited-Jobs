"""Collect from every source and rebuild data/jobs.csv (plan section 8).

Run: python -m collector.build_csv
"""
import csv
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

from collector import boards, schema, skills, usajobs

ROOT = Path(__file__).parent.parent
CSV_PATH = ROOT / "data" / "jobs.csv"
METROS_PATH = ROOT / "config" / "metros.yml"
MAX_ROWS = 500
# 125 remote + 375 non-remote, split about evenly between the metros
TARGETS = {"remote": 125, "Portland": 188, "Seattle": 187}

log = logging.getLogger("build_csv")


def load_metros(path=METROS_PATH):
    """Return {metro: (city_regex, state_regex)}."""
    out = {}
    for name, cfg in yaml.safe_load(Path(path).read_text()).items():
        cities = "|".join(re.escape(c) for c in cfg["cities"])
        states = "|".join(re.escape(s) for s in cfg["states"])
        out[name] = (re.compile(rf"\b(?:{cities})\b", re.I), re.compile(rf"\b(?:{states})\b"))
    return out


def match_metro(locations, metros):
    """First metro whose city (plus its state, if a state is given) appears in a location."""
    for loc in locations:
        for name, (city_rx, state_rx) in metros.items():
            if city_rx.search(loc) and ("," not in loc or state_rx.search(loc)):
                return name
    return ""


def _newest_first(jobs):
    # Blank dates sort last; job_id breaks ties so the output is stable week to week
    return sorted(jobs, key=lambda j: (j.get("date_posted", ""), j["job_id"]), reverse=True)


def dedupe(jobs):
    """Keep the newest copy per job_id, then per company + title + location."""
    seen_ids, seen_keys, out = set(), set(), []
    for job in _newest_first(jobs):
        key = (job.get("company", "").lower(), job.get("title", "").lower(),
               job.get("location", "").lower())
        if job["job_id"] in seen_ids or key in seen_keys:
            continue
        seen_ids.add(job["job_id"])
        seen_keys.add(key)
        out.append(job)
    return out


def select(groups, targets=TARGETS, max_rows=MAX_ROWS):
    """Fill each group up to its target, newest first, then backfill free slots."""
    chosen, leftovers = [], []
    for name, target in targets.items():
        group = _newest_first(groups.get(name, []))
        chosen += group[:target]
        leftovers += group[target:]
    free = max_rows - len(chosen)
    return chosen + _newest_first(leftovers)[:max(free, 0)]


def build(jobs, today, metros, patterns):
    """Pure rebuild: jobs from this run only, so gone jobs drop out (FR-5)."""
    groups, metro_of = {name: [] for name in TARGETS}, {}
    for job in dedupe(jobs):
        if job.get("remote"):
            groups["remote"].append(job)
            continue
        metro = match_metro(job.get("cities", []) + [job.get("location", "")], metros)
        if metro:  # non-remote jobs outside both metros are dropped
            metro_of[job["job_id"]] = metro
            groups[metro].append(job)
    rows = []
    for job in _newest_first(select(groups)):
        found = skills.find(f"{job.get('title', '')}\n{job.get('text', '')}", patterns)
        rows.append(schema.to_row(job, metro_of.get(job["job_id"], ""), found, today))
    return rows


def write_csv(rows, path=CSV_PATH):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=schema.COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def collect():
    """Run every source. Returns (jobs, failed_count, total_count)."""
    jobs, failed = usajobs.fetch_all()
    companies = boards.load_companies()
    board_jobs, board_failed = boards.fetch_all(companies)
    return jobs + board_jobs, failed + board_failed, len(usajobs.SEARCHES) + len(companies)


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        from dotenv import load_dotenv  # local runs only; the Action uses secrets
        load_dotenv(ROOT / ".env")
    except ImportError:
        pass
    jobs, failed, total = collect()
    if failed == total or not jobs:
        log.error("Every source failed; leaving %s unchanged", CSV_PATH.name)
        return 1
    today = datetime.now(timezone.utc).date().isoformat()
    rows = build(jobs, today, load_metros(), skills.load())
    write_csv(rows)
    counts = {}
    for r in rows:
        group = "remote" if r["remote"] == "true" else r["metro"]
        counts[group] = counts.get(group, 0) + 1
    log.info("Wrote %d rows %s (%d sources failed)", len(rows), counts, failed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
