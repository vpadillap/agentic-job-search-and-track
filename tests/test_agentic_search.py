"""provider-agentic-search: remembered companies, the source site of a posting, and the
provider file. Fictional companies only."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from jobtracker.core import companies, db, search, seasons

REPO = Path(__file__).resolve().parents[1]


def write(tmp_path, data, name="in.json") -> str:
    path = tmp_path / name
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return str(path)


ANDES = {"name": "Andes Datos Ficticios", "careers_url": "https://careers.andes.example/jobs/",
         "found_via": '"Data Engineer" Lima careers', "title": "Senior Data Engineer",
         "matches": 2}


# ── companies ─────────────────────────────────────────────────────────────

def test_companies_are_recorded_and_updated(searchable, cli, tmp_path):
    code, out, _ = cli("companies", "record", write(tmp_path, [ANDES]))
    assert code == 0 and len(out["created"]) == 1, out
    again = {**ANDES, "careers_url": "https://careers.andes.example/jobs", "matches": 0,
             "title": "Data Platform Engineer"}                  # same page, trailing / aside
    code, out, _ = cli("companies", "record", write(tmp_path, [again]))
    assert code == 0 and out["created"] == [] and len(out["updated"]) == 1
    _, listed, _ = cli("companies", "list")
    (company,) = listed["companies"]
    assert company["titles"] == ["Senior Data Engineer", "Data Platform Engineer"]
    assert company["last_matches"] == 0 and company["excluded"] is False


def test_excluding_and_including_a_company(searchable, cli, tmp_path):
    _, out, _ = cli("companies", "record", write(tmp_path, [ANDES]))
    company_id = str(out["created"][0])
    code, out, _ = cli("companies", "exclude", "https://careers.andes.example/jobs",
                       "--reason", "never show me Andes")
    assert code == 0 and out["company"]["excluded"] is True
    assert out["company"]["excluded_reason"] == "never show me Andes"
    assert cli("companies", "list")[1]["companies"] == []
    assert len(cli("companies", "list", "--excluded")[1]["companies"]) == 1
    # Found again later: stays excluded and is reported so it is not imported.
    _, again, _ = cli("companies", "record", write(tmp_path, [ANDES]))
    assert again["excluded"] == [int(company_id)]
    code, out, _ = cli("companies", "include", company_id)
    assert code == 0 and out["company"]["excluded"] is False


def test_a_new_season_starts_with_no_companies(searchable, cli, tmp_path):
    cli("companies", "record", write(tmp_path, [ANDES]))
    with db.session(searchable) as conn:
        seasons.start(conn, learning="keep", leave_open=True)
        assert companies.list_companies(conn, excluded=None) == []
        assert companies.summary(conn) == {"known": 0, "excluded": 0}


@pytest.mark.parametrize("record,field", [
    ({**ANDES, "name": " "}, "name"),
    ({**ANDES, "careers_url": "careers.andes.example"}, "careers_url"),
    ({**ANDES, "matches": -1}, "matches"),
    ({**ANDES, "title": 3}, "title"),
])
def test_invalid_companies_store_nothing(searchable, cli, tmp_path, record, field):
    code, out, _ = cli("companies", "record", write(tmp_path, [ANDES, record]))
    assert code == 1 and field in out["error"]["message"]
    assert cli("companies", "list", "--all")[1]["companies"] == []


def test_unknown_company_is_not_found(searchable, cli):
    code, out, _ = cli("companies", "exclude", "999")
    assert code == 1 and out["error"]["code"] == "not_found"


def test_context_counts_companies(searchable, cli, tmp_path):
    cli("companies", "record", write(tmp_path, [ANDES]))
    _, context, _ = cli("context")
    assert context["companies"] == {"known": 1, "excluded": 0}


# ── source site ───────────────────────────────────────────────────────────

def posting(**extra) -> dict:
    return {"provider": "alpha", "external_id": "https://careers.andes.example/jobs/42",
            "url": "https://careers.andes.example/jobs/42", "title": "Senior Data Engineer",
            "company": "Andes Datos Ficticios", "location": "Lima", "country": "PE",
            "description": "Buscamos un ingeniero de datos ficticio.", **extra}


def test_a_posting_keeps_its_source_site(searchable, cli, tmp_path):
    _, run, _ = cli("run", "start")
    code, report, _ = cli("postings", "import", str(run["run_id"]),
                          write(tmp_path, [posting(source_site="Careers.Andes.Example")]))
    assert code == 0 and report["new"] == 1, report
    with db.session(searchable) as conn:
        item = search.posting(conn, report["postings"][0]["posting_id"])
    assert item["source_site"] == "careers.andes.example"
    assert item["posted_at"] is None                         # no date given, none guessed


def test_source_site_is_optional_and_must_be_a_host(searchable, cli, tmp_path):
    _, run, _ = cli("run", "start")
    code, _, _ = cli("postings", "import", str(run["run_id"]), write(tmp_path, [posting()]))
    assert code == 0
    code, out, _ = cli("postings", "import", str(run["run_id"]),
                       write(tmp_path, [posting(external_id="x2", url="https://a.example/2",
                                                source_site="https://a.example/2")]))
    assert code == 1 and out["error"]["details"]["field"] == "source_site"


# ── provider file ─────────────────────────────────────────────────────────

def test_provider_file():
    from jobtracker.core import providers

    item = {p["id"]: p for p in providers.list_providers()}["agentic-search"]
    assert item["valid"], item["problems"]
    assert (item["access"], item["coverage"], item["requires_login"], item["dependencies"],
            item["max_results_per_query"]) == ("web-search", "global", False, ["playwright"],
                                               40)
    assert item["min_seconds_between_requests"] >= 5 and item["domains"] == []
    text = (REPO / "providers" / "agentic-search.md").read_text(encoding="utf-8")
    for required in ("jt companies list --all", "jt companies record -", "jt companies exclude",
                     "different companies", "15 companies", "source_site",
                     "publication date not shown", "Never use", "aggregators",
                     "jt providers read agentic-search", "--found", "robots.txt",
                     "12 searches", "Sector employers", "suggest_provider", "/add-provider",
                     "never type", "No stealth"):
        assert required in text, required
    # Every other provider file's site is named as one this provider never reads.
    sites = text.split("### Sites you never read here")[1].split("## Search recipe")[0]
    for other in providers.list_providers():
        if other["id"] != "agentic-search":
            assert f"| {other['id']} |" in sites, other["id"]
