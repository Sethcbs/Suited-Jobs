# Agentic Job Suitor: Project Plan

Oct 29, 2026 · @Mèo đen

## 1) Document control and ownership

| Field | Detail |
| --- | --- |
| Project ID / title | A-JOB-SUIT-001 / Agentic Job Suitor |
| Document owner | Seth Stigall |
| Business sponsor / reviewer | CSBS 431 / Professor Gill |
| Status | Proposed, awaiting review |
| Version / date | 1.1 (non-agentic) / October 29, 2026 |
| Planned delivery | November 1, 2026 for version 1.0 (ready to present by November 2). November 30, 2026 for the agentic version 2.0 |
| Repository | Public GitHub repository (link to be added) |
| Approval | Awaiting |

## 2) Executive summary and business problem

Agentic Job Suitor helps people find job postings that fit their skills without the hassle of searching multiple job sites by hand.

It can take a lot of time to look through job boards for the right positions that match a persons skills. Users may feel they don't have the time to rewrite their application materials, or even to start looking. I want to show users what applications match their skills, and provide priority skills they should highlight in their application material.&#32;

Version 1.0 (due November 1, 2026) collects recent postings from the free USAJOBS API and from company job boards every Friday and keeps the 500 most recent in a CSV on GitHub. A Flask page shows them, and people can filter by Portland metro, Seattle metro, or remote.

Version 2.0 (due November 30, 2026) adds an AI agent. A person uploads a PDF resume. The agent finds the skills in it, compares them with the skills in each posting, and returns the best matches with links and a reason for each. It also points out what to focus on in a resume and in an interview.

## 3) Objectives, outcomes, and success criteria

Version 1.0 covers collecting and showing the data. Version 2.0 adds the resume and the agent.

| ID | Objective | Success criteria | Version |
| --- | --- | --- | --- |
| O1 | Choose job sources with public APIs | USAJOBS and company job boards (Greenhouse, Lever, Ashby) are chosen as sources, and I have a working USAJOBS API key | 1.0 |
| O2 | Collect data with a GitHub Action and store it in a CSV on GitHub | The Action adds postings from USAJOBS and from at least one company board (Jama Software on Greenhouse) to the CSV automatically. The CSV holds at most 500 rows with no duplicates | 1.0 |
| O3 | Refresh the data every Friday | Run history shows a run started by the schedule, not by me, on Friday Oct 30 (or Friday Nov 6 if the workflow merges late, with a manual run shown for Nov 1) | 1.0 |
| O4 | Build a Flask page to display the data | The page shows the table and filters using dummy data | 1.0 |
| O5 | Connect the Flask page to the CSV on GitHub | The page shows rows read from the raw GitHub URL, and a change to the CSV shows up on the page | 1.0 |
| O6 | Learn how AI agents work and how they fit this task | I can describe in detail how an agent would read a resume, identify skills, and search the CSV (written in 1.0, built in 2.0) | 1.0 / 2.0 |
| O7 | Accept a resume in PDF format | The Flask page accepts a PDF and shows the text it extracted | 2.0 |
| O8 | Connect the AI to Flask and have it read the resume | The agent receives the resume text from Flask and returns the skills it found | 2.0 |
| O9 | Connect the AI to the CSV and have it filter jobs | The agent compares resume skills with job skills and points to specific CSV rows. Every job ID it returns exists in the CSV | 2.0 |

## 4) Project scope and boundaries

Version 1.0 is data collection and display only. The agent and resume features belong to version 2.0.

### In scope, version 1.0

- Job data from two kinds of sources: the USAJOBS API (federal job postings) and the public job boards of chosen companies on Greenhouse, Lever, and Ashby, starting with Jama Software on Greenhouse
- A GitHub Action that runs every Friday and writes the job data to a CSV in a public GitHub repository
- At most 500 rows in the CSV: 125 remote jobs and 375 non-remote jobs in the Seattle or Portland metro areas
- Keyword-based skill tags on every posting
- A Flask page, run locally, that reads the CSV from its raw GitHub URL and lets people filter it
- Documentation of the work and the pipeline

### In scope, version 2.0

- A PDF resume upload on the Flask page
- Keyword extraction from the resume
- An AI agent that reads the resume, searches the CSV, and returns job links with a reason for each match
- Short guidance on what to focus on in a resume and in an interview

### Out of scope

- Web scraping and any other non-API data collection
- A database or self-hosted storage
- Custom-trained models or new applications of AI agents
- Hosting the Flask page online (it runs locally)
- Storing uploaded resumes, and resume formats other than PDF
- Data storage security and any guarantee that a job is relevant

### Possible later expansion

These need a scope change and a check of each site's terms before I start them:

- Employers on Workday, such as Nike and Intel. Workday's documented recruiting API is for a company's own system, and its public careers endpoint is undocumented
- Bright Data as an extra collection tool for sites without an API
- More job sources, such as Adzuna on a paid plan (its free requests are too few), more companies on the job boards, and online hosting

### Assumptions

- The free USAJOBS API and the public company boards are enough for one weekly run
- The terms of USAJOBS and of each company board allow me to store a limited set of fields in a public repository (to be checked before the first commit)
- I do the development myself, with tutorials and AI assistance allowed

## 5) Stakeholders and responsibilities

I am the only developer, and Professor Gill reviews the work.

| Role | Responsibility |
| --- | --- |
| Developer (Seth) | Owner of all documentation, development, testing, and the deliverable |
| Reviewer (Professor Gill, CSBS 431) | Reviews the claims, validity, and accuracy of claims |
| Job seekers (intended users) | Browse postings and, in version 2.0, upload a resume to get matches |

## 6) Requirements and traceability

There are 15 functional and 5 non-functional requirements, and each objective in section 3 maps to at least one of them.

### Requirements

| ID | Requirement | Version |
| --- | --- | --- |
| FR-1 | Collect postings from the USAJOBS API and from company job boards on Greenhouse, Lever, and Ashby (Jama Software first) | 1.0 |
| FR-2 | Map every posting to the CSV schema. Unknown fields stay blank and are never guessed | 1.0 |
| FR-3 | Remove duplicates by job ID, and by company + title + location when two sources list the same job | 1.0 |
| FR-4 | Keep at most 500 rows: 125 remote and 375 non-remote. Fill every slot, cut the oldest when full, and backfill from the other group when one is short | 1.0 |
| FR-5 | Drop a job from the CSV when its source no longer lists it | 1.0 |
| FR-6 | Tag each job with skills found by matching a keyword list against its title and description | 1.0 |
| FR-7 | A GitHub Action writes data/jobs.csv to the repository | 1.0 |
| FR-8 | The Action runs every Friday on a schedule and can also be started by hand | 1.0 |
| FR-9 | The Flask page shows the table with filters for Portland metro, Seattle metro, remote, skill, and source | 1.0 |
| FR-10 | The Flask page reads the CSV from its raw GitHub URL | 1.0 |
| FR-11 | Accept a PDF resume and extract its text | 2.0 |
| FR-12 | Extract resume keywords with the same keyword list used for jobs | 2.0 |
| FR-13 | Rank jobs by the overlap between resume keywords and job skills | 2.0 |
| FR-14 | The agent returns job links with a reason for each, and every returned job ID exists in the CSV | 2.0 |
| FR-15 | Show resume guidance: skills common in the top matches that are missing from the resume | 2.0 |
| NFR-1 | API keys live in GitHub Secrets and are never committed to the public repository | 1.0 |
| NFR-2 | Collection uses no AI service or account | 1.0 |
| NFR-3 | The CSV stores only the fields in section 8, with a short description snippet, because the repository is public | 1.0 |
| NFR-4 | Uploaded resumes are not stored | 2.0 |
| NFR-5 | Total cost stays near $10 (a soft limit), with $5 loaded for now | 2.0 |

### Traceability

| Objective | Requirements |
| --- | --- |
| O1 Find job sources | FR-1 |
| O2 GitHub Action stores data in a CSV | FR-2 to FR-7, NFR-1 to NFR-3 |
| O3 Friday refresh | FR-8 |
| O4 Flask page | FR-9 |
| O5 Flask reads the CSV on GitHub | FR-10 |
| O6 Learn how agents work | FR-14, FR-15 |
| O7 Accept a PDF resume | FR-11, NFR-4 |
| O8 AI reads the resume | FR-11, FR-12 |
| O9 AI filters jobs from the CSV | FR-13, FR-14 |

## 7) Data sources

Version 1.0 pulls from the USAJOBS API and from public company job boards, all through official or public APIs, with no scraping.

| Source | What it gives me | Access | Notes |
| --- | --- | --- | --- |
| USAJOBS API | Federal job postings with title, organization, location, pay range, publication and closing dates, and a link | Free API key, requested by email at developer.usajobs.gov. Each request sends three headers: Host, User-Agent (my registered email), and Authorization-Key | Federal jobs only, so every posting comes from a government agency. The site has a tutorial with example search requests. I have the key |
| Company job boards: Greenhouse | Every open job a company lists on its public board, with title, location, link, and a last-updated date. Adding content=true brings the descriptions | No key. `GET https://boards-api.greenhouse.io/v1/boards/{slug}/jobs` | Greenhouse's help site describes the Job Board API for building career sites, and only submitting an application needs a key. The list has no salary, and a wrong slug returns a 404. The whole board comes back in one response with no paging. Jama Software is confirmed on Greenhouse (slug jamasoftware) |
| Company job boards: Lever | Every published posting, with a created date, a workplace type that includes remote, team, and sometimes a salary range | No key. `GET https://api.lever.co/v0/postings/{slug}?mode=json`. Companies hosted in the EU use api.eu.lever.co | Lever documents the postings API on GitHub. It can sometimes return HTML instead of JSON, so I check the response type and retry |
| Company job boards: Ashby | Every published posting, with a published date, a remote flag, a workplace type, and compensation when the company shares it | No key. `GET https://api.ashbyhq.com/posting-api/job-board/{name}?includeCompensation=true` | Board names are case-sensitive. The whole board comes back in one response, and the public endpoint has no search or filters, so I filter after fetching |

I dropped Adzuna for now because its free requests are too few for weekly runs. Each company needs its board name (its slug), which I read from the link on its careers page. Jama Software is the only company confirmed so far, so Lever and Ashby support stays ready until I find a company on each. The endpoints are public, but the postings belong to the companies, so I will check each company's terms before committing its rows to the public repository.

## 8) Data design

The CSV holds at most 500 rows: 125 remote and 375 non-remote. It is rebuilt from USAJOBS and the company boards on every run.

### CSV schema

The first eight fields in my original list are here, plus the columns I need for filtering and linking.

| Column | Description |
| --- | --- |
| job\_id | Source name plus the source's own ID for the posting, such as usajobs:123456, so IDs never collide |
| source | usajobs, greenhouse, lever, or ashby |
| title | Job title |
| company | The agency (USAJOBS) or the company (job boards) that posted the job |
| location | Location text from the source |
| metro | Portland, Seattle, or blank for remote jobs |
| remote | true or false |
| salary | Pay range as listed, blank if missing (Greenhouse lists none) |
| skills | Keywords found in the posting, separated by a vertical bar |
| url | Link to the posting |
| description\_snippet | Start of the posting's text, about 300 characters (my starting limit) |
| date\_posted | Date the source lists as the posting's publication or creation date |
| date\_fetched | Date of the run that collected it |

### Rules

1. **Fill first.** Each run collects more candidates than 500, so every slot fills on the first run. I page through the USAJOBS results until I have enough. Greenhouse, Lever, and Ashby return a whole board at once.
2. **Remote flag.** USAJOBS accepts Remote as a location, so one search covers remote jobs. Lever and Ashby give a workplace type or remote flag. Greenhouse doesn't, so I read the location text. I will confirm how remote jobs show up in the real responses, and otherwise look for the word remote in the title and location.
3. **Metro.** For non-remote jobs, I search USAJOBS by location for each metro, and I take every job from the company boards. I then match each job's location against city lists in config/metros.yml, for example Portland, Beaverton, and Hillsboro for Portland, and Seattle, Bellevue, and Redmond for Seattle. The full lists still need to be written. Non-remote jobs outside both lists are dropped.
4. **Split.** The target is 125 remote and 375 non-remote rows. I split the non-remote rows about evenly between Portland and Seattle so one city doesn't crowd out the other. This is an assumption I can change.
5. **Cut.** Within each group, I sort by date\_posted with the newest first and cut the oldest when the group is over its target. Greenhouse can reset its update date in bulk, so for Greenhouse I use the first-published date when the API gives one.
6. **Backfill.** If a group has fewer jobs than its target, the free slots go to the next newest jobs from the other groups, so the CSV holds 500 rows whenever enough jobs exist. The Portland and Seattle groups may be short, so the CSV may end up with more than 25% remote jobs.
7. **Duplicates.** I remove repeats by job\_id, and by company + title + location when two sources list the same job. The same posting can also show up in more than one USAJOBS search, such as a remote search and a city search, so I keep one row.
8. **Drop gone jobs.** Each run rebuilds the table from what the sources return that week, so a job a source no longer lists disappears. For company boards this is exact, because they return every open job. USAJOBS returns search results, so a missing job might be outside the search window and not closed. I fetch enough pages to cover the newest postings and let older ones age out.
9. **Blanks.** Missing fields stay blank. Nothing is guessed.
10. **Fetch date.** date\_fetched is the date of the run.

## 9) Collection pipeline and schedule

A GitHub Action runs every Friday, rebuilds data/jobs.csv from USAJOBS and the company boards, and commits it to the repository. The collection step uses no AI service.

&#91;embedded content: collection pipeline · USAJOBS and company boards to 1 CSV\]

USAJOBS (searched for Portland, Seattle, and remote) and the company boards feed one step that builds the table.

**Schedule.** The cron expression is `0 14 * * 5`, which is Friday 14:00 UTC. GitHub schedules run in UTC, so that is 7:00 AM Pacific until daylight saving ends on November 1, and 6:00 AM after. The workflow can also be started by hand. A scheduled workflow only runs from the default branch, so I need to merge it today, October 29, for the first scheduled run to fire on Friday, October 30. Scheduled runs can start late.

**Steps in each run.**

1. Check out the repository and install the Python packages
2. Run the USAJOBS collector (one search each for Portland, Seattle, and remote jobs) and the company-board collector (one request per company in config/companies.yml)
3. Convert every posting to the CSV schema, remove duplicates, and tag skills
4. Apply the 500-row rules from section 8
5. Write data/jobs.csv
6. Commit and push only if the file changed

**If a search fails,** the run logs the error and continues with the others. If every search and board fails, the CSV is left as it was, so the page never goes blank.

**Secrets.** The USAJOBS key and my registered email are stored as GitHub Secrets and never committed, since the repository is public. The workflow needs permission to write to the repository contents so it can push the CSV.

**Planned repository layout** (file names may change):

```
suited-jobs/
  .github/workflows/weekly-refresh.yml
  collector/
    usajobs.py, boards.py               (one collector per source type)
    schema.py, skills.py, build_csv.py
  config/
    companies.yml, skills.yml, metros.yml
  data/jobs.csv
  app/                                  (Flask page)
  docs/
```

## 10) Flask application

The Flask page reads data/jobs.csv from the public repository's raw GitHub URL and shows it as a table people can filter. It runs on my computer.

**Data source.** The page fetches `https://raw.githubusercontent.com/<user>/<repo>/main/data/jobs.csv` (user, repo, and branch name to be filled in). It keeps a short cache so it doesn't call GitHub on every refresh, and it falls back to the last copy it fetched if GitHub can't be reached.

**Build order.** I build the page on dummy rows first, then point it at the real URL. This keeps page problems separate from data problems.

**Filters.** Portland metro, Seattle metro, and remote (any combination), skill keyword, and source. Rows sort by date\_posted, newest first. Each row shows the title, company, location, salary, skills, date posted, and a link to the posting.

**Version 2.0 additions.** A PDF upload form, and a results view that lists the agent's matches with a reason for each, plus the resume guidance.

## 11) Skill matching design

I match skills with a keyword list on both sides, jobs and resumes, so the two can be compared directly.

- **One keyword file.** config/skills.yml holds each skill's standard name and its aliases, such as JS for JavaScript and Postgres for PostgreSQL. I start with common languages, frameworks, databases, cloud services, and tools, and grow the list as test postings show gaps.
- **How matching works.** It is case-insensitive and matches whole words. C++, C#, .NET, and Node.js need special handling. Short names like Go, R, and C need care so they don't match ordinary words.
- **Jobs (version 1.0).** At collection time I match the list against each posting's title and the description text each source returns, and store the standard names in the skills column.
- **Resumes (version 2.0).** I extract the text from the PDF and run the same matcher to get the resume's keywords.
- **Score.** A job's score is the number of its skills that appear in the resume, divided by the number of skills found in the job. Jobs with no skills found rank last. The page also shows which skills matched and which are missing.

**Limits I accept.** Federal postings may name skills differently from private-sector ones, and I still need to check how much description text the USAJOBS API returns, since less text means fewer skills found. Company boards usually give full descriptions, so I expect more skills from them. Anything outside the list is invisible. A keyword match isn't understanding, so a posting that says a skill is not required still counts. A scanned PDF with no text layer can't be read. The matcher is also a baseline I can compare the AI agent against later.

## 12) Agent design (version 2.0)

The agent turns a PDF resume into a short ranked list of job links, each with a reason. It uses four tools in a loop and never invents a job.

| Tool | Input | Output |
| --- | --- | --- |
| ingest\_resume | The uploaded PDF | The resume text |
| get\_skills | The resume text | Keywords found with the skills list, and which look most important |
| search\_jobs | Skills, plus the person's choice of Portland, Seattle, or remote | Matching rows from the CSV |
| get\_job | A job ID | The full CSV row for that job |

**The loop.**

1. Flask passes the PDF to ingest\_resume and gets the resume text.
2. The agent calls get\_skills and decides which skills matter most.
3. It calls search\_jobs with those skills and the person's location choice.
4. For promising results, it calls get\_job to read the details.
5. It returns a short ranked list. Each entry has the job ID, link, matching skills, a reason, and what the resume is missing.
6. My code checks that every returned job ID exists in the CSV. Any ID that doesn't is dropped and flagged.
7. Flask shows the matches and the resume guidance.

**Model and cost.** I start with a tool-use loop on the Claude API, to learn how agents work in practice. The four tools are plain Python functions with JSON-schema descriptions, with a thin adapter for each model provider, so another model can be swapped in. The collection pipeline never depends on any of this. I filter jobs in code before sending anything to the model, to keep cost near $10 (a soft limit). The resume is sent with each request and is not stored.

## 13) Timeline and milestones

Version 1.0 is due November 1, so I have four days. Friday, October 30 is my one chance to show a scheduled run before then.

&#91;embedded content: version 1.0 timeline · Oct 29 to Nov 2\]

The workflow has to be on the default branch by the end of today, October 29, for the schedule to fire on Friday, October 30. If it isn't, I show the workflow with a manual run, and the first scheduled run is Friday, November 6. The Flask page starts on dummy data and switches to the real CSV once USAJOBS works. The Jama Software board on Greenhouse comes after that, and Lever and Ashby only if time allows.

**Version 2.0 (November 2 to November 30).** Resume upload and keyword extraction, the four agent tools and loop, the results page, testing with two resumes, documentation, and delivery on November 30.

## 14) Verification and test plan

Every requirement has a check I can run and a pass condition. Version 1.0 checks run against real source data.

| Check | How | Passes when | Version |
| --- | --- | --- | --- |
| CSV rules (FR-2 to FR-4) | Run the collector, then count rows, duplicates, and groups | At most 500 rows, no repeated job\_id, and 125 remote and 375 non-remote when enough jobs exist (otherwise backfilled). Unknown fields are blank | 1.0 |
| Drop rule (FR-5) | Remove a job from a test source and run again | The job is gone from the CSV | 1.0 |
| Skill tags (FR-6) | Run the matcher on test postings that have known keywords | The expected skills are found, with no false hits for short names like Go, R, and C | 1.0 |
| Schedule (FR-8) | Look at the Actions run history | A run triggered by the schedule appears on Friday Oct 30 (or Nov 6 if the workflow merges late), with no input from me | 1.0 |
| Secrets (NFR-1) | Search the repository and its history for keys | None found | 1.0 |
| Flask filters (FR-9) | Test each filter on dummy rows, then on the real CSV | Counts for Portland, Seattle, and remote match the CSV | 1.0 |
| Raw URL (FR-10) | Edit the CSV on GitHub and reload the page after the cache expires | The page shows the change | 1.0 |
| Resume extraction (FR-11, FR-12) | Upload test PDFs | Text and keywords are extracted. A non-PDF or unreadable file is rejected with a clear message | 2.0 |
| Agent matches (FR-13, FR-14) | Run two test resumes: one with many relevant skills and one with many non-relevant skills | The first gets job links with a reason for each. The second gets few or weak matches and says so. Every returned job ID exists in the CSV | 2.0 |
| Guidance (FR-15) | Read the guidance for both test resumes | The missing skills it lists are common in the top matches | 2.0 |
| Privacy (NFR-4) | Review the code and the files after an upload | No resume file or text is stored | 2.0 |

**Done means** the section 3 criteria for O1 to O5 are met and the Actions history shows a scheduled run (version 1.0), and the criteria for O6 to O9 are met (version 2.0).

## 15) Risks, assumptions, and open questions

The biggest risks are a source's terms and limits, and the four days left before version 1.0.

| Risk | Plan |
| --- | --- |
| A source's terms or limits don't allow what I planned. USAJOBS and the company boards each have their own | Read the terms before the first commit and store only the fields in section 8 |
| A source's requests fail or its endpoint changes. Greenhouse can change or withdraw its board endpoint | Log the error and skip that source. If every source fails, keep the old CSV |
| A company's board name is wrong or its board is empty | A wrong Greenhouse name returns a 404, and an empty board is valid. I log it, skip it, and check the careers-page link for the right name |
| Lever sometimes returns HTML instead of JSON | Check the response type, retry once, then skip |
| Greenhouse update dates can be reset in bulk | Use the first-published date when the API gives one, and note it when it doesn't |
| Remote jobs are flagged inconsistently | Use Lever's and Ashby's own flags, read Greenhouse's location text, fall back to keyword detection, and accept some errors |
| Few federal jobs in Portland and Seattle, or few with tech skills | The backfill rule in section 8, and the company boards for private-sector jobs |
| The scheduled run starts late or stops. GitHub can disable schedules on inactive repositories, and I will check its current rules | Keep the manual trigger, watch the Actions page, and merge the workflow today |
| The keyword list misses skills or matches wrongly | Grow the list from test postings and keep the skill-tag check in the test plan |
| Not enough time before November 1 | Build in order: USAJOBS end to end, the Flask page, then Jama Software on Greenhouse. Lever and Ashby only if time allows |
| My $5 of API credit runs out while building, or before version 2.0 | Work in small steps, check usage often, and top up before starting the agent |
| The public repository exposes data and mistakes | No secrets in the repository, and a note in the README about where the data comes from |

### Open questions

- Which other companies on Lever and Ashby go on the list? Only Jama Software (Greenhouse) is confirmed so far
- What are the exact Portland and Seattle city lists?
- Should non-remote jobs split evenly between the two metros?
- How does USAJOBS mark remote jobs, and which text fields does it return for skill matching?
- Does Jama Software's Greenhouse list give a first-published date, or only an update date?
- What are the repository name, user, and branch for the raw URL?

## Sources

The facts about each source come from these pages as they appeared in search results on October 21 and October 29, 2026. Before I rely on any limit or term, I will confirm it in the provider's own documentation.

- [USAJOBS Search Jobs tutorial](https://developer.usajobs.gov/Tutorials/Search-Jobs)
- [USAJOBS API explained (JobsPipe)](https://jobspipe.dev/blog/usajobs-api): required headers and the Remote location
- [USAJOBS Scraper (Apify)](https://apify.com/maydit/usajobs-scraper.md): fields the search returns
- [Greenhouse API overview (Greenhouse help site)](https://support.greenhouse.io/hc/en-us/articles/10568627186203-Greenhouse-API-overview): the Job Board API, and that only applications need a key
- [Integration with Greenhouse public jobs API (DEV Community)](https://dev.to/zsevic/integration-with-greenhouse-public-jobs-api-1lj3): endpoint, content=true, and job fields
- [Greenhouse Jobs Scraper (Apify)](https://apify.com/appdata-labs/greenhouse-jobs): whole board in one response, with no paging
- [Jama Software careers (Greenhouse)](https://boards.greenhouse.io/jamasoftware/jobs/6512088): confirms Jama Software uses Greenhouse
- [Lever API guide for 2026 (100Hires)](https://100hires.com/lever-api.html): public postings endpoint, and the HTML-instead-of-JSON problem
- [Integration with Lever public jobs API (DEV Community)](https://dev.to/zsevic/integration-with-lever-public-jobs-api-2mnn): EU host, created date, and paging
- [Ashby API: pulling job postings (JobsPipe)](https://jobspipe.dev/blog/ashby-api-jobs.md): unauthenticated, one company per call
- [Ashby Jobs Scraper (Apify)](https://apify.com/ratio_tech/ashby-scraper): board names and compensation option
- [Adzuna API field guide (JobsPipe)](https://jobspipe.dev/blog/adzuna-api): free-tier limits, reported differently by different sources
- [Workday job boards have a JSON API too (DEV Community)](https://dev.to/udaninn/workday-job-boards-have-a-json-api-too-its-just-better-hidden-23fl): undocumented public careers endpoint
- [How to get your Workday API keys (Apideck)](https://www.apideck.com/blog/how-to-get-your-workday-api-keys): Workday's documented API needs the company's own credentials
