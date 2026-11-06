"""The agent's tools as plain Python, with no AI in them (plan section 12).

One JobTools holds one person's resume text and their jobs, already filtered to the
places they chose. The model can't search outside those jobs or ask for another resume.
"""
SEARCH_LIMIT = 20
SEARCH_FIELDS = ["job_id", "title", "company", "location", "metro", "remote", "salary",
                 "date_posted"]


def row_skills(row):
    return [s for s in row["skills"].split("|") if s]


class JobTools:
    def __init__(self, rows, resume_text, patterns):
        self.rows = {row["job_id"]: row for row in rows}
        self.resume_text = resume_text
        self.patterns = patterns

    def get_skills(self):
        """Resume skills from the keyword list, most mentioned first."""
        counts = [(name, len(rx.findall(self.resume_text))) for name, rx in self.patterns]
        found = sorted((c for c in counts if c[1]), key=lambda c: -c[1])
        return {"skills": [{"skill": name, "mentions": n} for name, n in found]}

    def resume_skills(self):
        return {s["skill"] for s in self.get_skills()["skills"]}

    def search_jobs(self, skills, limit=SEARCH_LIMIT):
        """Jobs ranked by overlap with skills (FR-13): most skills matched, then highest score.

        Score = matched / job's skills. It can't go first, or a job listing a single skill
        scores 1.0 and pushes out jobs that match far more. Jobs with no listed skills rank last.
        """
        wanted = {s.strip().lower() for s in skills}
        scored = []
        for row in self.rows.values():
            job_skills = row_skills(row)
            matched = [s for s in job_skills if s.lower() in wanted]
            if job_skills and not matched:
                continue
            score = len(matched) / len(job_skills) if job_skills else 0.0
            scored.append((len(matched), score, row["date_posted"], row["job_id"], matched))
        scored.sort(reverse=True)
        jobs = [{**{f: self.rows[job_id][f] for f in SEARCH_FIELDS},
                 "skills": row_skills(self.rows[job_id]), "matched_skills": matched,
                 "score": round(score, 2)}
                for _count, score, _date, job_id, matched in scored[:limit]]
        return {"total_found": len(scored), "jobs": jobs}

    def get_job(self, job_id):
        """The full CSV row, or None if this person's jobs don't include that ID."""
        return self.rows.get(job_id)
