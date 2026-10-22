"""Run: python -m pytest tests/  (fixtures are real Firecrawl output, 2026-09-15)

The page parser keeps data engineering titles only: pages read this way have
no JD, so a generic title could never pass the JD gate in select()."""
from pathlib import Path
import jobscan as J

FX = Path(__file__).parent

def jobs(name):
    return J.parse_markdown_jobs((FX / f"fx_{name}.md").read_text())

def test_goldman_cards_keep_per_role_urls():
    got = {j["title"]: j["url"] for j in jobs("goldman")}
    title = "Asset & Wealth Management - PWM Data Engineering - Vice President - Bengaluru"
    assert got == {title: "https://higher.gs.com/roles/168761"}

def test_one_word_datawarehouse_is_a_de_title():
    got = {j["title"]: j["url"] for j in jobs("siemens")}
    assert got == {"Sr Software Engineer (Datawarehouse)":
                   "https://jobs.siemens.com/en_US/externaljobs/JobDetail/512517"}

def test_sde_only_pages_yield_nothing():
    # Tesco's page also carries Apply / job-alert links; none read as a role
    assert jobs("tesco") == []
    assert jobs("satsure") == []

def test_lilly_phenom_cards_title_first():
    # Phenom card markdown puts title on its own line above a separate
    # "Location\n<city>" block, unlike Tesco/Siemens/Goldman's single-line
    # cards - this is the shape most Phenom sites use.
    got = {j["title"]: j["location"] for j in jobs("lilly")}
    assert got == {"Associate Director, Data Engineering": "Bangalore"}
    # the parser only finds roles; title_ok() then drops the director grade
    assert not J.title_ok("Associate Director, Data Engineering")
