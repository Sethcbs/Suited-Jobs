import pytest

from collector import build_csv, schema, skills


@pytest.fixture(scope="module")
def patterns():
    return skills.load()


@pytest.fixture(scope="module")
def metros():
    return build_csv.load_metros()


def job(n, remote=False, city="Portland, Oregon", date="2026-10-01", **kw):
    return {"job_id": f"t:{n}", "source": "usajobs", "title": f"Job {n}", "company": "Agency",
            "location": city, "cities": [city], "remote": remote, "date_posted": date,
            "text": "Requires Python.", **kw}


# --- skills (FR-6) ---
@pytest.mark.parametrize("text,expected", [
    ("Python, SQL and C++ on Linux", ["Python", "C++", "SQL", "Linux"]),
    ("Experience with C# and ASP.NET", ["C#", ".NET"]),
    ("Built with Node.js and React.", ["React", "Node.js"]),
    ("Programs in C and R, plus Rust and Excel", ["C", "R", "Rust", "Excel"]),
    ("Golang services", ["Go"]),
])
def test_skills_found(patterns, text, expected):
    assert skills.find(text, patterns) == expected


@pytest.mark.parametrize("text", [
    "Go to the office. Let's go.", "R&D lab", "C-suite briefing", "Grade C/R ratings",
    "the river and car", "Section c. of form", "rusty javelin",
    "per 6 C.F.R. 37", "Schedule A, Schedule C or Non", "Pay Band C (AD-13)",
    "Schedule, C, Non-career", "apply oils, rust inhibitor", "excel at swift work",
])
def test_no_false_hits(patterns, text):
    assert skills.find(text, patterns) == []


# --- metro ---
@pytest.mark.parametrize("loc,expected", [
    ("Portland, Oregon", "Portland"), ("Hillsboro, OR", "Portland"),
    ("Vancouver, Washington", "Portland"), ("Bellevue, WA", "Seattle"),
    ("Seattle", "Seattle"), ("Portland, Maine", ""), ("Vancouver, British Columbia", ""),
    ("Location Negotiable After Selection", ""),
])
def test_match_metro(metros, loc, expected):
    assert build_csv.match_metro([loc], metros) == expected


# --- dedupe (FR-3) ---
def test_dedupe_by_id_and_by_company_title_location():
    jobs = [job(1), job(1), job(2, date="2026-10-05", title="Same", location="X"),
            job(3, date="2026-10-01", title="Same", location="X")]
    out = build_csv.dedupe(jobs)
    assert sorted(j["job_id"] for j in out) == ["t:1", "t:2"]  # newest copy kept


# --- cap, split, backfill (FR-4) ---
def test_cap_and_split_when_enough_jobs(metros, patterns):
    jobs = ([job(f"r{i}", remote=True) for i in range(200)]
            + [job(f"p{i}") for i in range(300)]
            + [job(f"s{i}", city="Seattle, Washington") for i in range(300)])
    rows = build_csv.build(jobs, "2026-10-30", metros, patterns)
    counts = {g: sum(1 for r in rows if (r["metro"] or "remote") == g)
              for g in ["remote", "Portland", "Seattle"]}
    assert len(rows) == 500
    assert counts == {"remote": 125, "Portland": 188, "Seattle": 187}
    assert len({r["job_id"] for r in rows}) == 500


def test_cut_keeps_newest(metros, patterns):
    jobs = ([job(f"old{i}", remote=True, date="2026-01-01") for i in range(5)]
            + [job(f"r{i}", remote=True, date="2026-09-01") for i in range(125)])
    rows = build_csv.build(jobs, "2026-10-30", metros, patterns)
    assert len(rows) == 130  # backfill lets all remote in, since metros are empty
    jobs += [job(f"p{i}") for i in range(400)] + [job(f"s{i}", city="Seattle") for i in range(400)]
    rows = build_csv.build(jobs, "2026-10-30", metros, patterns)
    remote_dates = [r["date_posted"] for r in rows if r["remote"] == "true"]
    assert len(remote_dates) == 125 and "2026-01-01" not in remote_dates


def test_backfill_when_group_short(metros, patterns):
    jobs = ([job(f"r{i}", remote=True) for i in range(40)]
            + [job(f"p{i}") for i in range(500)]
            + [job(f"s{i}", city="Seattle, Washington") for i in range(500)])
    rows = build_csv.build(jobs, "2026-10-30", metros, patterns)
    assert len(rows) == 500
    assert sum(r["remote"] == "true" for r in rows) == 40


def test_drops_jobs_outside_metros_and_gone_jobs(metros, patterns):
    week1 = [job(1), job(2), job(3, city="Denver, Colorado")]
    assert {r["job_id"] for r in build_csv.build(week1, "d", metros, patterns)} == {"t:1", "t:2"}
    week2 = [job(1)]  # source no longer lists job 2 (FR-5)
    assert {r["job_id"] for r in build_csv.build(week2, "d", metros, patterns)} == {"t:1"}


# --- tech jobs only ---
def test_drops_jobs_with_no_skills(metros, patterns):
    jobs = [job(1), job(2, text="Provides patient care.")]
    rows = build_csv.build(jobs, "d", metros, patterns)
    assert [r["job_id"] for r in rows] == ["t:1"]
    assert rows[0]["skills"] == "Python"


def test_a_skill_in_the_title_is_enough(metros, patterns):
    rows = build_csv.build([job(1, title="Python Developer", text="")], "d", metros, patterns)
    assert [r["skills"] for r in rows] == ["Python"]


def test_jobs_with_no_skills_do_not_take_slots(metros, patterns):
    newer = [job(f"new{i}", date="2026-10-02", text="No keywords.") for i in range(600)]
    older = [job(f"old{i}", date="2026-01-01") for i in range(10)]
    rows = build_csv.build(newer + older, "d", metros, patterns)
    assert len(rows) == 10 and all(r["job_id"].startswith("t:old") for r in rows)


def test_main_keeps_old_csv_when_no_job_has_skills(monkeypatch):
    def fail_if_written(rows):
        raise AssertionError("CSV should not be written")
    monkeypatch.setattr(build_csv, "collect", lambda: ([job(1, text="No keywords.")], 0, 1))
    monkeypatch.setattr(build_csv, "write_csv", fail_if_written)
    assert build_csv.main() == 1


# --- schema / blanks (FR-2) ---
def test_cities_win_over_location_text(metros, patterns):
    foreign = job(1, location="Vancouver", cities=[])  # a board left it out as abroad
    joined = job(2, location="Portland, ME; Seattle, WA", cities=["Portland, ME", "Seattle, WA"])
    rows = build_csv.build([foreign, joined], "2026-11-06", metros, patterns)
    assert [(r["job_id"], r["metro"]) for r in rows] == [(joined["job_id"], "Seattle")]


def test_location_is_used_when_a_job_has_no_cities_field(metros, patterns):
    no_cities = job(1)
    del no_cities["cities"]
    rows = build_csv.build([no_cities], "2026-11-06", metros, patterns)
    assert rows[0]["metro"] == "Portland"


def test_row_has_all_columns_and_blanks(metros, patterns):
    rows = build_csv.build([job(1, remote=True, date="")], "2026-10-30", metros, patterns)
    row = rows[0]
    assert list(row) == schema.COLUMNS
    assert row["metro"] == "" and row["salary"] == "" and row["date_posted"] == ""
    assert row["date_fetched"] == "2026-10-30"


def test_snippet_is_short():
    assert len(schema.snippet("word " * 200)) <= schema.SNIPPET_LEN + 3
