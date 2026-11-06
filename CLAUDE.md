# Suited Jobs (Agentic Job Suitor) — CSBS 431

Full plan: docs/PLAN.md (long; read only the section you need).

## Version 2.0 (due Nov 30, 2026) — resume matching agent, in progress
- `/match` on the Flask page reads a PDF in memory (`app/resume.py`) and runs a tool-use loop on the Claude API (`app/agent.py`) over plain Python tools (`app/tools.py`).
- Links, titles, and skill lists come from the CSV in code. The model only chooses jobs and explains them. Unknown job IDs are dropped and flagged.
- Never store or log resume text. Tests use a fake client and never call the real API. Real API runs cost money, so ask first.
- Model is `claude-opus-5-5` unless `SUITED_JOBS_MODEL` is set.

## Version 1.0 (due Nov 1, 2026) — collection and display
- A GitHub Action (every Friday, cron `0 14 * * 5`, plus workflow_dispatch) collects postings and writes `data/jobs.csv`.
- Sources: USAJOBS API (searches: Portland, Seattle, Remote) and public company boards
  (Greenhouse first: Jama Software, slug `jamasoftware`; Lever/Ashby only if time allows).
- A local Flask page in `app/` reads the CSV from its raw GitHub URL and filters by metro, remote, skill, and source.

## Hard rules
- Public APIs only. No scraping. No AI calls during collection. Skip Workday, Adzuna, ZipRecruiter, and Bright Data.
- Secrets: `USAJOBS_API_KEY` and `USAJOBS_USER_AGENT_EMAIL` come from env vars only (gitignored `.env` locally, GitHub Secrets in the Action).
  Never print, log, or commit them. `ANTHROPIC_API_KEY` follows the same rule, and only the Flask page uses it.
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
- Non-tech jobs are dropped before the row limits apply, so the CSV can hold fewer than 500 rows. A job is tech if it has a skill outside `general` in config/skills.yml or its title matches `tech_titles`.

## Layout
collector/ (usajobs.py, boards.py, schema.py, skills.py, build_csv.py) · config/ (companies.yml, skills.yml, metros.yml)
· data/jobs.csv · app/ · tests/ · .github/workflows/weekly-refresh.yml
