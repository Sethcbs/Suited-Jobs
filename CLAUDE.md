# Suited Jobs (Agentic Job Suitor) — CSBS 431

Full plan: docs/PLAN.md (long; read only the section you need).

## Version 1.0 (due Nov 1, 2026) — no AI agent yet (that is 2.0)
- A GitHub Action (every Friday, cron `0 14 * * 5`, plus workflow_dispatch) collects postings and writes `data/jobs.csv`.
- Sources: USAJOBS API (searches: Portland, Seattle, Remote) and public company boards
  (Greenhouse first: Jama Software, slug `jamasoftware`; Lever/Ashby only if time allows).
- A local Flask page in `app/` reads the CSV from its raw GitHub URL and filters by metro, remote, skill, and source.

## Hard rules
- Public APIs only. No scraping. No AI calls during collection. Skip Workday, Adzuna, ZipRecruiter, and Bright Data.
- Secrets: `USAJOBS_API_KEY` and `USAJOBS_USER_AGENT_EMAIL` come from env vars only (gitignored `.env` locally, GitHub Secrets in the Action).
  Never print, log, or commit them.
- Never guess field values. Unknown CSV fields stay blank. Check unknowns against a real API response.
- Keep steps small, and commit after each step with tests passing (`.venv/bin/pytest -q`).

## CSV rules (plan section 8)
Columns: job_id, source, title, company, location, metro, remote, salary, skills, url,
description_snippet, date_posted, date_fetched.
- job_id = `source:id`. skills are joined with `|`. The snippet is about 300 chars. metro is Portland, Seattle, or blank for remote.
- Max 500 rows: 125 remote and 375 non-remote (split evenly between Portland and Seattle). Newest date_posted wins.
  Short groups backfill from the others.
- Dedupe by job_id, then by company + title + location.
- Each run rebuilds the table from the sources, so jobs a source stops returning drop out.
  If every source fails, leave the old CSV unchanged.
- Non-remote jobs whose location isn't in config/metros.yml are dropped.

## Layout
collector/ (usajobs.py, boards.py, schema.py, skills.py, build_csv.py) · config/ (companies.yml, skills.yml, metros.yml)
· data/jobs.csv · app/ · tests/ · .github/workflows/weekly-refresh.yml
