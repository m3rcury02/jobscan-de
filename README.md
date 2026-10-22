# jobscan-de

Polls company ATS boards every hour, filters to India-based **data engineering** roles whose
stated experience band starts at 2 years or less (`MY_YOE` = 2, `YOE_STRETCH` = 0), fetches
the full job description, scores it against your data engineering stack, and emails a digest
that opens with the handful of roles to apply to first.

The data engineering twin of [jobscan](https://github.com/m3rcury02/jobscan), which does the
same for SDE roles. Same engine and adapters, 371 boards: jobscan's whole board list plus 22
data-heavy employers added on 2026-10-22 (Tredence, Quantiphi, Blend360, Mastercard, Barclays,
Target, Maersk, Experian, Snowflake, Tekion, dunnhumby and others). Roles at companies where you have a referral
are tagged *REFERRAL* and ranked up.

No API keys for the job boards. All endpoints are public.

## What differs from jobscan

Only the profile and the filters. Everything that fetches boards is jobscan's code, unchanged.

| | jobscan (SDE) | jobscan-de |
|---|---|---|
| Titles | any engineering title: "developer", "software engineer", "SRE" ... | data engineering titles (`TITLE_KEEP`, plus ETL/ELT/DWH as words) |
| Generic titles ("Software Engineer II", "Senior System Engineer") | kept | JD fetched, kept only if it scores `DE_JD_MIN_POINTS` (7) of data-specific skills; SQL, Python and AWS do not count |
| Years | band includes 2; 3+ kept as *stretch* | band starts at 2 or below; 3+ dropped |
| Skills | Java / Spring / AI banks | resume packet Section 6B: Strong 3, Working knowledge 2, adjacent 1 |
| Gaps | Go, C++, Spark, Airflow ... | Azure, GCP, BigQuery, Kafka, Kinesis, streaming, Hadoop/Hive, Informatica, Power BI ... |
| Role points (20%) | backend / AI titles highest | DE titles highest; roles on Azure or GCP rather than AWS get 6 of 20 |
| Email subject | `Jobs <date>: ...` | `DE jobs <date>: ...` |

**Porting a fix from jobscan.** Adapter and engine fixes land in jobscan first. The profile
lives in four places in `jobscan.py`: the block from `MY_YOE` to `GAP_RE`, the block from
`TITLE_KEEP` to `TITLE_DROP`, `title_ok` / `is_de_title` / `de_jd_points`, and
`other_cloud` / `role_points`. The JD gate is one `if` in `select()`, and the page adapters
call `is_de_title` where jobscan reads `TITLE_KEEP`. Any other hunk in a jobscan diff applies
here as is.

**The same role in both digests.** jobscan's `TITLE_KEEP` includes "data engineer", so a data
engineering role reaches both inboxes, scored twice against different stacks. Trust this one's
score for DE roles. To stop the duplicates, drop "data engineer" from jobscan's `TITLE_KEEP`.

## Setup (10 minutes)

1. **Repo secrets.** Settings > Secrets and variables > Actions > New repository secret. The
   same values as jobscan (secrets are per repo, so they have to be added again):
   - `SMTP_USER` = gunal.works@gmail.com
   - `SMTP_PASS` = the 16-character Gmail app password
   - `SMTP_TO` = gunal.works@gmail.com
   - optional, for tailored resumes: `RESUME_PACKET`, `RESUME_INSTRUCTIONS`, and
     `CLAUDE_CODE_OAUTH_TOKEN` or `ANTHROPIC_API_KEY` (see "Tailored resumes" below)

2. **Run `backlog` once.** Actions > jobscan-de > Run workflow > mode `backlog`. A new scanner
   with an empty `seen.json` would otherwise only ever show roles posted in the last 2 days;
   `backlog` reports every open data engineering role up to 90 days old, once.

3. **Set up the hourly trigger** (see "Hourly runs" below). The workflow's own cron is only a
   backup.

`companies.csv` is already filled. To add a company, put its name in `wanted.txt` and run
`discover` mode. `wanted.txt` holds the 49 data employers still uncovered on 2026-10-22, each
with the reason. Tiger Analytics is the one most worth finishing, and it is one `curl` away (the
file says how); the rest run Zoho Recruit, TurboHire, Jobvite, Taleo or a JavaScript-only page.

## Hourly runs

GitHub's scheduler drops most scheduled runs (jobscan saw `17 * * * *` fire twice in 14
hours). An outside scheduler that triggers the workflow is what makes it hourly:

1. **Token.** Edit the fine-grained token you made for jobscan (GitHub > Settings > Developer
   settings > Personal access tokens) and add `jobscan-de` to its repository access, or make a
   new one: repository access `jobscan-de` only, Actions = Read and write, nothing else.
2. **Scheduler.** At cron-job.org, add a second cron job:
   - URL: `https://api.github.com/repos/m3rcury02/jobscan-de/actions/workflows/jobscan.yml/dispatches`
   - Schedule: every hour, at minute **47** (jobscan polls at :17; keeping them half an hour
     apart avoids the 429s two overlapping polls drew from Workable and Workday)
   - Advanced > Request method: `POST`
   - Headers: `Authorization: Bearer <the token>`, `Accept: application/vnd.github+json`,
     `X-GitHub-Api-Version: 2022-11-28`
   - Request body: `{"ref":"main","inputs":{"mode":"scan","max_age":"2"}}`
   - It should report HTTP 204.

Hourly needs a public repo (unlimited Actions minutes). This one is public for that reason, like
jobscan. Nothing private is committed: secrets stay in repo secrets, and the scanner prints only
counts to the log.

## Modes

Actions > jobscan-de > Run workflow > mode:

| mode | what it does |
|---|---|
| `scan` | the default, and what the cron runs. Roles from the last 2 days. |
| `backlog` | repairs seen.json, then reports every open role up to 90 days old. Run once after adding boards. |
| `discover` | reads `wanted.txt`, finds each company's board, writes verified ones to `companies.csv`. |
| `diagnose` | probes every board and reports why each failure happened. Run monthly. |
| `prune` | comments out every row `diagnose` found returning 404. |
| `dry-run` | prints the digest, sends nothing. |
| `applied` | records an application: paste the posting URL, pick a status. No checkout needed - it runs in Actions. |

## Files

- `companies.csv` - your target board list. The only file you edit regularly.
- `wanted.txt` - companies to find boards for. `discover` mode reads this.
- `careers_urls.txt` - hand-supplied careers URLs, with the outcome of each recorded.
- `seen.json` - URLs already reported. Prevents repeat digests. Committed by CI.
- `applied.csv` - your applications. Written by `applied` mode or by hand; the scanner only
  reads it (follow-up nudges, and a flag on new roles at companies you applied to recently).
- `pipeline.csv` - one row per role found, with years band, score and digest section. The
  scanner owns it; `Status`/`AppliedDate` are the only columns it will not overwrite.
- `fetch_errors.log` - boards that failed, with reason.
- `board_health.json` - last good poll per board; drives BOARDS DOWN. Committed by CI.
- `daily_sent.txt` - IST date of the last once-a-day email (follow-ups, boards down).
- `dead_rows.txt` - written by `diagnose`, consumed by `prune`.
- `discover.py` - board discovery. Separate from the scanner; only runs in `discover` mode.
- `resumes.py` - tailored resumes for APPLY FIRST roles. Off until its secrets exist.

## The Referral column

A row with `Referral = yes` has its roles tagged `*REFERRAL*` in the digest and in
`pipeline.csv`, ranked above a slightly better match without one, and given the
referral-first instruction. It also skips `COMPANY_DROP`, which since 2026-10-01 holds only
staffing agencies: a role someone can walk you into is worth seeing whoever posted it.

## Boards down

`board_health.json` records each board's last good poll and how many roles it returned.
A board that has failed for 6 hours, or come back with 0 roles after having 5 or more,
is listed under **BOARDS DOWN** at the top of the digest, referral companies first, and
gets one email a day even when nothing new turned up. Before this, TCS returned nothing
for five days (its careers site moved to a new API) and five RippleHire boards failed on
a third of runs, and the only sign was a count in the digest footer. If a board is still
listed after you have checked it really has no openings, comment its row out.

## seen.json is "already emailed", nothing else

This file decides what you never see again, so the one rule that matters: only ever add
a URL to it that was actually sent to you. An earlier version also added anything older
than the freshness window, which silently buried 547 open roles - the digest showed 16 a
day while hundreds sat hidden.

`python jobscan.py --repair-seen` rebuilds it from `pipeline.csv`, which is the real
record of what was sent. Run it if the digest ever goes suspiciously quiet.
It also leaves out rows that were found but never really shown - the title-scored
Workday/Oracle rows and the 404ing SmartRecruiters links from before 2026-09-25 - so
the `backlog` run that follows re-checks them with their full JD.

## Tuning

Edit the constants at the top of `jobscan.py`. The values here were calibrated on 2026-10-22
against a live poll of every board (52,969 roles, 27,304 in India) and the JDs of every
matching role posted in the last 30 days. The figures below are that month re-judged with the
code as shipped.

- `MY_YOE` / `YOE_STRETCH` - 2 and 0: a role is kept when the band its JD states starts at 2
  years or less ("0-2", "1-3", "2-5", "2+"), and dropped when it asks 3+. A band you are past
  ("0-1", "freshers only") is kept but ranked lower. **This is the setting that costs the most
  roles.** Over the 30 days it dropped 367: 47 asking exactly 3 years, 37 asking 4, and 283
  asking 5 or more. Of the 106 it kept, 31 stated a band you fit and 74 stated none.
  `YOE_STRETCH = 1` would add the 47 three-year roles, marked *stretch*, as jobscan does.
- `HAS_MASTERS` - "Bachelor's + 7 years OR Master's + 4 years" is read on the Bachelor's
  route unless this is True. Left False as in jobscan. Your M.Tech Integrated is a Master's on
  paper; set it True if you are happy to apply on that route.
- `CORE_SKILLS` / `SECONDARY_SKILLS` / `SUPPORT_SKILLS` - weighted keyword banks, matched as
  whole words, taken from the resume packet's self-rating (6B): Strong 3, Working knowledge
  2, adjacent confirmed stack 1. Only skills the packet backs belong here, because the digest
  tells you to mirror every hit in your resume. Snowflake and dbt are 1, not 2: the packet
  says they have no system behind them yet. Move a skill up as the packet's rating does.
- `GAP_SKILLS` - the packet's NOT SUPPORTED list (6A) and awareness-only skills, shown as
  "JD also wants". Remove an entry when you add that skill to a bank.
- `MAX_SKILL_POINTS` - 30. Skill points across 769 DE-titled JDs: median 17, p75 25, p90 34.
  jobscan's 24 saturated 29 of the 106 kept roles and tied 12 of them at 88; 30 saturates 15.
- `DE_JD_MIN_POINTS` - 7, counted without SQL, Python, AWS, Git and S3, which every backend JD
  names. 220 of 3,683 generic-title JDs pass. At 7-8 points they already read as data work
  (Microsoft SDE II: Spark, ETL; Amazon BIE II: ETL, Redshift, warehouse); below that they are
  backend roles that mention a pipeline.
- `TITLE_KEEP` / `GENERIC_TITLE_KEEP` / `TITLE_DROP` - if you see junk, add the offending word
  to `TITLE_DROP` rather than raising a threshold.
- `COMPANY_DROP` - staffing agencies.
- `MORE_PER_COMPANY` - roles listed per company in the longer digest sections before a
  "+N more at X" line. Persistent posted seven "Azure Data Engineer" roles in one month;
  this keeps one firm from burying the rest. Every role is in `pipeline.csv` regardless.
- `APPLY_FIRST_MAX` / `PER_COMPANY_CAP` / `REFERRAL_BONUS` - the shape of the top list.

**What a month looks like.** The 30-day calibration kept 106 roles with a JD, about 25 a week,
plus a few title-only ones. Most come from IT services firms and captives (Virtusa 22,
Persistent 12, Infosys 11, EXL 9, Capgemini 6); 44 were at referral companies, and 7 were
generic titles that only the JD gate caught. Product companies post few data
engineering roles at 0-2 years, which is the reason to finish Tiger Analytics and to look at
the consultancies in `wanted.txt` by hand.

### How a role is judged

1. Cheap filters on the list data: new, not a staffing agency, a data engineering title or
   a generic engineering one (`GENERIC_TITLE_KEEP`), India, posted within `--max-age` days.
2. One detail call per survivor fetches the full JD (Workday, SmartRecruiters, Oracle,
   Eightfold; the other boards include it already). A failed fetch is logged and the role
   is shown as title-only, never scored on nothing.
3. Is it data engineering? A data engineering title is. A generic title ("Software Engineer
   II", Infosys's "Senior System Engineer") is kept only when its JD scores
   `DE_JD_MIN_POINTS` from the CORE and SECONDARY banks - Spark, Glue, Airflow, a warehouse,
   and so on. SQL, Python, AWS, Git, S3 and the SUPPORT bank do not count, because every
   backend JD names them. A generic title whose JD fetch failed is dropped: nothing shows it
   is DE.
4. Years: a band in the title wins ("Exp: 4-8 Yrs"); otherwise the highest minimum across
   the required lines - "3+ years of development, 2+ of design" asks for 3. Preferred /
   nice-to-have lines, Master's/PhD routes and company history ("for 40 years") are
   ignored. Graduation-year-gated roles ("2026 batch") are dropped. Junior phrasings are
   read as bands: "up to 2 years" and "less than 2 years" as 0-2 (not 2+), "Freshers to
   2 years", "Min 0 Max 2", "Experience Required: 0-2 Yrs", "6 months to 2 years",
   "0-24 months".
5. Seniority: "Senior", "Sr", "III" and "Staff Engineer" titles are kept only when the JD
   states a band you are in. Indian product companies do post
   "Senior (2-4 yrs)", and Altimetrik's "Staff Engineer" is 2-5; without that evidence a
   senior title reads as 4-6+ years. Fresher / trainee / graduate / new-grad titles work
   the other way: kept only when the JD's band includes your years ("Trainee Data
   Engineer, 0-2 yrs"); the rest are campus programmes you have aged out of.
6. Score: 50% weighted skill overlap, 30% years fit (in-band 30, unstated 18, below 15),
   20% role type. Role type is 20 for a data engineering title, 16 for a warehouse or
   platform title, 12 for "SQL Developer", 8 for a generic title the JD proved, and 6 for a
   role on Azure or GCP rather than AWS (the title names one of them and not AWS, or the JD
   names them twice and never AWS). Deterministic and cheap. If it disagrees with your
   judgement, the keyword bank is wrong, not the formula.

## Tailored resumes for APPLY FIRST roles

Each APPLY FIRST role that has a job description gets your resume generator run on it, and
the result is attached to the digest as a markdown file: a one-page resume when your
eligibility gate scores 90 or above, otherwise the gate's audit (score, failed checks, and
the minimum points that would clear 90). The digest line under the role says which. It is
the same as pasting the JD into your claude.ai Project, which cannot be called from a script.

**Setup.** Repo Settings > Secrets and variables > Actions:

1. `RESUME_PACKET` - the full resume source packet (markdown).
2. `RESUME_INSTRUCTIONS` - the Project instructions, eligibility gate included.
3. One way to reach Claude:
   - `CLAUDE_CODE_OAUTH_TOKEN` - your Claude subscription. Run `claude setup-token` on your
     own machine (Claude Code installed, signed in) and paste the token it prints. No extra
     cost; it draws on the same usage limits as your interactive Claude use. The run installs
     the Claude Code CLI only when this route is in use.
   - or `ANTHROPIC_API_KEY` - the Anthropic API, paid per use (console.anthropic.com).
     About $0.10-0.20 a resume on Claude Opus 5.5 at the default effort. Wins if both are set.

**Model.** Claude Opus 5.5 at `xhigh` effort on both routes. If your plan does not offer
Opus 5.5, the CLI route retries on your plan's default model and the digest line says so.
Measured against `high` on the same JD: 443 s and 2.6x the tokens, with no gain on the
instructions' mechanical rules and more metric-bank figures attached to specific workflows,
so check those figures before you send. `RESUME_EFFORT=high` is the faster option.

Optional repository variables (not secrets): `RESUME_MODEL`, `RESUME_EFFORT`, `RESUME_MAX`
(per run, default 8). Resumes are only generated when the SMTP secrets are set, since they travel by
email.

**What it costs in time.** Measured: 33 s for an audit, about 2.5 min for a full resume.
Up to 8 per run (`RESUME_MAX`), 3 at a time, within a 25-minute budget at `xhigh` (15 at
`high`); anything still
running then is marked "not generated" and the digest goes out without it.

**Privacy.** The packet, the instructions and every resume carry your phone number and email,
and this repo and its Actions logs are public. Keep them in secrets, never in a file here.
The scanner writes nothing to the repo and prints only counts to the log; resumes travel by
email only. Dry runs never generate (they would print to the public log).

**Data engineering resumes.** Nothing in `resumes.py` is DE-specific: the packet's Section 9
("use for data engineer, ETL, data integration, and data platform JDs") is what routes these
JDs to the data engineering view, so keep Section 9 in the `RESUME_PACKET` secret. The
packet's [VERIFY] items for [SYS-J], [SYS-K] and [SYS-M] keep some of your strongest bullets
off every resume until you answer them; answering them is worth more here than in jobscan.

**Read before you send.** These are drafts. A real run on a Java role produced a 518-word
resume that followed the format and left unsupported JD keywords out, but also merged two
unrelated facts into one bullet. Roles outside Bangalore lose 5 gate points unless the
packet says whether you will relocate.

## Workflow

The digest opens with **APPLY FIRST**: at most 8 roles, at most 2 per company, ranked by
fit score plus a referral bonus plus freshness. Each one carries its years band, the
skills from your stack the JD asks for (mirror those in the tailored resume - only ones
you have), what else the JD wants, and the next step.

1. Referral company? Send the link to your referrer and let them submit you *before*
   you apply. An existing application usually blocks or voids the referral.
2. Otherwise open the URL, read the JD, generate the tailored resume, apply by hand -
   ideally within 48 hours of posting.
3. Record it: Actions > jobscan-de > Run workflow > mode `applied`, paste the URL, pick a
   status (`referred` if a referrer submitted you). Update the status the same way.
4. The first digest at or after 07:30 IST each day lists applications 7-21 days old
   that still read `applied` or `referred`, with the follow-up to send.
   (`daily_sent.txt` records the day it went out.) New roles at a company you applied to in the
   last 30 days are flagged and demoted: one strong application per company beats five.

## Adapters

| ATS value | notes |
|---|---|
| `greenhouse` `lever` `ashby` `smartrecruiters` `workable` | plain GET, public JSON |
| `workday` | POST. Token = site, Tenant = `<name>.wdN`. See below. |
| `oracle` | Token = site number (often `CX_1`), Tenant = full oraclecloud host |
| `keka` | Token = subdomain. Two GETs to learn the tenant id, one to read jobs. |
| `eightfold` | Token = subdomain, Tenant = the `domain=` param. Caps pages at 10. |
| `successfactors` | Token = host, e.g. `jobs.ametek.com`. Two page templates exist; both parsed. |
| `pinpoint` | Token = subdomain. Public JSON at `/postings.json`. No posting dates. |
| `amazon` | no token needed. Filters on `normalized_country_code`, not the fuzzy loc_query. |
| `custom` `agency` | plain GET plus text heuristics. See below. |
| `firecrawl` | Token = full search URL, Tenant = waitFor ms. Real browser via Firecrawl; once a day. See below. |
| `phenom` | Token = the site's search-results URL. Reads refNum/pageId from the page, then pages `/widgets`. Real dates. |
| `sfcsb` | SuccessFactors Career Site Builder (newer template). Token = host; Tenant = optional `field=value` facet. |
| `infosys` `tcs` `capgemini` | single-company APIs. TCS: `/candidate/next` API (moved 2026-10-01), XSRF token from the session call; no dates, so all ~1,800 India roles are read. |
| `zwayam` | Token = careers base URL, Tenant = Zwayam company id (COMPANYID in the site's main.js). |
| `ripplehire` | Token = subdomain, Tenant = careers token, optionally `\|geo=India` (LTIMindtree only; other tenants return 0 with it). No dates, so every role is read. Sessions without a JSESSIONID get empty replies and are renewed. |
| `avature` | Token = the portal's SearchJobs URL (keywords may sit in the path). Tenant = location to assume for "Multiple Locations". |
| `selectminds` | Oracle SelectMinds. Token = site root. No dates. |
| `techmahindra` | ASP.NET form postbacks. Title, band and skills only; the link names the Job Reference ID to search. |
| `jibe` | iCIMS Jibe sites. Token = host, Tenant = location. Unit (e.g. Epsilon) appended to the title. |
| `rss` | A site's own job feed: RSS `<item>` or Indeed-style `<job>`. Token = feed URL, Tenant = country to keep. |
| `freshteam` | Token = subdomain. Reads the public widget feed (`/hire/widgets/jobs.json`): every published job with JD, branch and date. The `/jobs` page `custom` used to scrape showed a fraction of them. `agency` rows on Freshteam use it too. |
| `pcsx` | Eightfold's newer career-site API. Token = host (`apply.careers.microsoft.com`), Tenant = the `domain=` param. Use it where `eightfold`'s `/api/apply/v2` returns 403 (Microsoft, Qualcomm, Infineon, Morgan Stanley). |

`successfactors` reads the real result count ("of 2,242") and sorts newest first. Before
2026-10-01 it read the page range as the total and stopped after 25 roles on every board.
`oracle` likewise sorts newest first and pages past 200.

Naukri is deliberately absent: it needs a headless browser and its listings skew heavily
toward IT services bulk hiring.

## IT services firms

Added 2026-10-01. None has a board on the ATS platforms `discover.py` probes, so each
source was read out of the careers site's own JavaScript: TCS iBegin, the Infosys careers
API, SuccessFactors CSB (Wipro, HCLTech), Zwayam (Persistent, Coforge, Cyient), RippleHire
(LTIMindtree, Mphasis, Altimetrik, Tata Technologies), Capgemini's job-search API, Oracle
HCM (Hexaware, Zensar, EXL, KPMG), SuccessFactors (Birlasoft, EY, Atos), Workday (NTT DATA,
DXC) and Phenom (Quest Global). Most publish the experience band as data, so the years
filter works on them even where the JD prose does not state it.

What to expect: bands at these firms are wide ("4-14 years") and often start above 3, so
the years filter drops a large share. TCS, LTIMindtree, Capgemini, EY and the RippleHire
boards publish no posting date; their first scan after being added reports every open role
once, then only new ones.

Also reached, in a second pass: Cognizant (its own XML job feed - the careers pages are
behind Cloudflare for browsers, the feed is not), Tech Mahindra (form postbacks), Deloitte
India (Avature), Virtusa (SelectMinds), Publicis Groupe incl. Sapient and Epsilon (iCIMS
Jibe), Unisys (Workday), UST (RippleHire), Brillio (Lever) and Mastek (SuccessFactors).
Tesco and Siemens moved off Firecrawl onto the Avature adapter, and Goldman Sachs onto
the Oracle adapter (higher.gs.com is a front end over its Oracle site `LateralHiring`), so
no row needs Firecrawl any more. Postman moved to Workday and Amplitude to Ashby in
2026-10.

Still not covered: EPAM India (Cloudflare WAF block even for a real browser, from any
datacenter IP), GlobalLogic (its job search call returns 403 to datacenter IPs, browser
included), Happiest Minds (Darwinbox behind a Cloudflare Turnstile check), and KPIT (needs
a real browser to pass a JavaScript check; Playwright on every hourly run adds a browser
install and a minute or more per run for one board). `remaining_companies.md` has the
full list of what is still uncovered and why.

## Companies with no ATS (custom careers pages)

Add them with `ATS = custom` and the full careers URL as the `Token`:

```
MoveInSync,custom,https://moveinsync.com/join-us,,
```

The adapter does a plain GET, then keyword-matches title-shaped lines in the
page text. No per-site selectors, nothing to maintain when a site is restyled.

Two consequences worth understanding:

**No posting date.** These pages don't publish one, so the 2-day window cannot
apply. Instead they are dated by first sighting: a role is reported the first
scan it appears in, then recorded in `seen.json` and never shown again. Running
daily makes this equivalent to a 1-day window.

**No job description.** Scoring them against your stack would be meaningless, so
they go to the digest's TITLE MATCH ONLY section unscored. Open the page to judge.

**JavaScript-rendered pages return nothing.** The plain GET sees no jobs and the
row quietly finds zero roles. If you suspect this, open the careers URL with JS
disabled - if the jobs vanish, the page needs a headless browser and is not
worth the maintenance.

### Finding whether a company actually has an ATS

Most "custom" careers pages are an ATS behind a vanity domain. Before adding a
`custom` row, check:

1. Open the careers page and click Apply. Watch where it redirects.
2. View source and search for: greenhouse, lever, ashby, workable,
   smartrecruiters, keka, darwinbox, zohorecruit, myworkdayjobs, icims.
3. Google `site:job-boards.greenhouse.io "company name"`, then the same for
   jobs.lever.co and jobs.ashbyhq.com.

If any of those hit, use the real ATS adapter instead. You get posting dates,
full descriptions and proper scoring - all three of which `custom` loses.

## Recruitment consultancies (ATS type `agency`)

Six staffing and recruitment boards are included with `ATS = agency`. They are
scraped like `custom` rows but routed to the digest's AGENCY section and never scored,
because their postings do not name the hiring company.

**Why they are separated rather than excluded.** Agencies genuinely surface
roles that never reach a public board, and some place well at product
companies. But an unnamed JD cannot be researched, cannot be matched against
your stack, and cannot be used to tailor a resume - so scoring it would be
fiction.

**The rule that matters.** Before applying through an agency, search a
distinctive phrase from the JD to work out who the employer is. If that company
has a direct board in this file, apply there instead. Recruitment agencies
claim candidate ownership for a period after submitting you - typically six to
twelve months - and a company faced with a fee claim will often drop the
candidate rather than pay. Applying through two channels is the fastest way to
lose a role you would otherwise have got.

**Also watch for:** the same role posted by three agencies at once, "immediate
joiners only" listings that ignore your notice period, and firms that submit
your resume to clients without asking first. Ask before you send anything.

## Workday (ATS type `workday`)

Workday's job list is a POST endpoint rather than a GET, so it needs its own
adapter. Read both values off any Workday careers URL:

```
https://cisco.wd5.myworkdayjobs.com/en-US/Cisco_Careers/job/...
             ^ Tenant = cisco.wd5       ^ Token = Cisco_Careers
```

Workday matters because it is where the India engineering centres of large
global companies sit. It is also the fiddliest adapter, for two reasons.

**The shard in the careers URL is not always the shard the API lives on.**
Omnissa's careers URL says `wd5`; its tenant is on `wd501`. 7-Eleven's says
`wd5`; it is on `wd3`. `discover.py` sweeps thirteen shards for this reason.

**Read the status code, not your intuition.** With one valid payload held
constant:

```
cisco.wd5 + Cisco_Careers -> 200      cisco.wd5 + BOGUS -> 404
cisco.wd1 + Cisco_Careers -> 422      cisco.wd1 + BOGUS -> 422
```

Since that body returns 200, a 422 is not schema rejection. 422 means the
tenant is not on that shard - try the next one. 404 means it is, and only the
site name is wrong - start guessing site names. Site names are arbitrary
strings: Cardinal Health's is `Ext`, HPE's is `Jobsathpe`, Citi's is `2`.

Dates arrive relative ("Posted 3 Days Ago", "Posted Today", "Posted 30+ Days
Ago") and are converted to real dates, so the recency window works normally.

The adapter sends `searchText: "India"` and pages up to `WORKDAY_MAX` (600)
results per board. Some tenants report the real total on page one and 0 on
every page after, so the loop keeps the largest total it has seen rather than
trusting each page - without that, Accenture truncated at 40 of 600.

## Firecrawl (ATS type `firecrawl`)

For careers pages that only render in a browser: Next.js sites, Avature, and
anything where `custom` finds zero roles. Add the repo secret
`FIRECRAWL_API_KEY`. Rows without it log an error and are skipped.

```
Example Co,firecrawl,https://careers.example.com/search?q=engineer&location=India,8000,,
```

No row uses it at present (the last, Goldman Sachs, moved to the `oracle` adapter).

It requests markdown (1 credit a page) and reads `[title](url)` links, so
every role keeps its real URL, unlike `custom`'s `page#slug`. Dates are rarely
present, so these roles fall back to first-sighting dating like `custom`.

**Cost.** Firecrawl rows run only on the UTC hours in `FIRECRAWL_HOURS_UTC`
(default `2`, i.e. 07:30 IST, once a day) during scheduled scans, and on every
manual mode. Five rows use about 150 credits a month. Putting a row on every
2-hour scan would use 12x that.

**What it will not fix.** Workday serves headless browsers a fake outage page;
use the `workday` adapter. Pages behind a candidate login (some Darwinbox
tenants) have nothing public to read. A slug that does not exist is still a
slug that does not exist: check the page text before blaming rendering.

Tests: `pip install pytest && python -m pytest tests/`. Firecrawl fixtures are real
output; the years-of-experience cases are lines lifted from live JDs.
