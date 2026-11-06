import pytest

from app.tools import JobTools
from collector import skills


def row(job_id, job_skills, date="2026-10-01"):
    return {"job_id": job_id, "title": f"Job {job_id}", "company": "Acme", "location": "Portland, OR",
            "metro": "Portland", "remote": "false", "salary": "", "skills": "|".join(job_skills),
            "url": f"https://example.com/{job_id}", "description_snippet": "Text.",
            "date_posted": date, "source": "lever", "date_fetched": "2026-11-06"}


@pytest.fixture
def tools():
    rows = [row("a", ["Python", "SQL"]), row("b", ["Python", "SQL", "AWS", "Docker"]),
            row("c", ["Java"]), row("d", [])]
    return JobTools(rows, "Python, Python and SQL on AWS", skills.load())


def test_get_skills_counts_mentions_most_first(tools):
    assert tools.get_skills()["skills"] == [
        {"skill": "Python", "mentions": 2}, {"skill": "SQL", "mentions": 1},
        {"skill": "AWS", "mentions": 1}]


def test_many_matched_skills_beat_a_perfect_score_on_one_skill():
    wanted = ["Python", "AWS", "Docker", "Kubernetes", "SQL"]
    rows = [row(f"one{i}", ["Python"], "2026-11-01") for i in range(25)]
    rows.append(row("strong", wanted + ["Java", "C#"], "2026-01-01"))
    jobs = JobTools(rows, "", []).search_jobs(wanted)["jobs"]
    assert jobs[0]["job_id"] == "strong" and jobs[0]["score"] == 0.71


def test_search_ranks_equal_matches_by_share_of_job_skills(tools):
    jobs = tools.search_jobs(["Python", "SQL"])["jobs"]
    assert [(j["job_id"], j["score"]) for j in jobs] == [("a", 1.0), ("b", 0.5), ("d", 0.0)]
    assert jobs[1]["matched_skills"] == ["Python", "SQL"]
    assert jobs[1]["skills"] == ["Python", "SQL", "AWS", "Docker"]


def test_search_ignores_case_and_skips_jobs_with_no_overlap(tools):
    ids = [j["job_id"] for j in tools.search_jobs(["python"])["jobs"]]
    assert "c" not in ids and ids[-1] == "d"  # no listed skills rank last


def test_search_orders_by_matched_count_then_score_then_newest():
    rows = [row("old", ["Python"], "2026-01-01"), row("new", ["Python"], "2026-10-01"),
            row("two", ["Python", "SQL"], "2025-01-01")]
    ids = [j["job_id"] for j in JobTools(rows, "", []).search_jobs(["Python", "SQL"])["jobs"]]
    assert ids == ["two", "new", "old"]


def test_newest_unlisted_jobs_keep_slots_when_many_jobs_match():
    rows = [row(f"m{i}", ["Python"]) for i in range(30)]
    rows += [row(f"u{i}", [], f"2026-10-{i + 10}") for i in range(8)]
    result = JobTools(rows, "", []).search_jobs(["Python"])
    ids = [j["job_id"] for j in result["jobs"]]
    assert len(ids) == 20 and result["total_found"] == 38
    assert ids[-5:] == ["u7", "u6", "u5", "u4", "u3"]  # last, and newest first
    assert all(i.startswith("m") for i in ids[:15])


def test_unused_slots_go_to_whichever_jobs_exist():
    few_unlisted = [row(f"m{i}", ["Python"]) for i in range(30)] + [row("u", [])]
    ids = [j["job_id"] for j in JobTools(few_unlisted, "", []).search_jobs(["Python"])["jobs"]]
    assert len(ids) == 20 and ids[-1] == "u" and sum(i.startswith("m") for i in ids) == 19

    few_matched = [row("m", ["Python"])] + [row(f"u{i}", []) for i in range(30)]
    ids = [j["job_id"] for j in JobTools(few_matched, "", []).search_jobs(["Python"])["jobs"]]
    assert len(ids) == 20 and ids[0] == "m"


def test_search_limit_reports_total():
    rows = [row(str(i), ["Python"]) for i in range(30)]
    result = JobTools(rows, "", []).search_jobs(["Python"])
    assert result["total_found"] == 30 and len(result["jobs"]) == 20


def test_get_job_returns_row_or_none(tools):
    assert tools.get_job("a")["url"] == "https://example.com/a"
    assert tools.get_job("nope") is None
