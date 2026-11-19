"""salary-suggestions: two-source gate, comparability, transparency, absence, reuse."""
from __future__ import annotations

import json
from datetime import datetime, timedelta

import pytest

from jobtracker.core import db, salary
from tests.test_search import captures

TODAY = datetime.now().date()


def report(**overrides) -> dict:
    base = {
        "source": "Example Salaries", "url": "https://example.test/salaries/1",
        "summary": "Fictional report", "amount_min": 14000, "amount_max": 16000,
        "currency": "PEN", "basis": "gross", "period": "month", "sample_size": 4,
        "observed_on": (TODAY - timedelta(days=40)).isoformat(), "country": "PE",
        "level": "Senior", "work_mode": "remote", "industry": "Retail",
        "company_size": "1,000+",
    }
    base.update(overrides)
    return base


@pytest.fixture
def postings(searchable, cli, tmp_path) -> dict:
    path = tmp_path / "captures.json"
    path.write_text(json.dumps(captures()), encoding="utf-8")
    _, run, _ = cli("run", "start")
    _, imported, _ = cli("postings", "import", str(run["run_id"]), str(path))
    return {p["external_id"]: p.get("posting_id") for p in imported["postings"]}


@pytest.fixture
def run_json(cli, tmp_path):
    def run(*args, data):
        path = tmp_path / "in.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        return cli(*args, str(path))
    return run


def add(run_json, posting_id: int, *records: dict) -> list[int]:
    code, out, _ = run_json("salary", "evidence", "add",
                            data=[{**r, "posting_id": posting_id} for r in records])
    assert code == 0, out
    return [e["id"] for e in out["evidence"]]


def suggest(run_json, posting_id: int, ids: list[int], **criteria):
    return run_json("salary", "set", str(posting_id),
                    data={"evidence_ids": ids, "criteria": {"currency": "PEN", **criteria},
                          "note": "Market reports for this role and level."})


def test_one_source_is_rejected_and_shows_no_data(searchable, postings, run_json):
    posting = postings["A-100"]
    ids = add(run_json, posting, report())
    code, out, _ = suggest(run_json, posting, ids)
    assert code == 1 and out["error"]["code"] == "insufficient_evidence"
    with db.session(searchable) as conn:
        assert salary.current(conn, posting) is None


def test_two_comparable_sources_store_amount_range_and_confidence(postings, run_json):
    posting = postings["A-100"]
    ids = add(run_json, posting, report(),
              report(url="https://example.test/salaries/2", amount_min=12000, amount_max=14000))
    code, out, _ = suggest(run_json, posting, ids, industry="Retail", company_size="1,000+")
    assert code == 0, out
    stored = out["salary"]
    assert stored["status"] == "suggested"
    assert stored["amount"] == 14000
    assert (stored["range_min"], stored["range_max"]) == (12000, 16000)
    assert stored["confidence"] == "medium"
    assert stored["basis"] == "gross" and stored["period"] == "month"
    assert [e["url"] for e in stored["evidence"]] == [
        "https://example.test/salaries/1", "https://example.test/salaries/2"]


def test_three_close_sources_give_high_confidence(postings, run_json):
    posting = postings["A-100"]
    ids = add(run_json, posting, report(), report(url="https://example.test/s/2"),
              report(url="https://example.test/s/3"))
    _, out, _ = suggest(run_json, posting, ids, industry="Retail", company_size="1,000+")
    assert out["salary"]["confidence"] == "high"


@pytest.mark.parametrize("bad,reason", [
    ({"country": "CL"}, "different country"),
    ({"level": "Junior"}, "different level"),
    ({"currency": "USD"}, "different currency"),
    ({"observed_on": (TODAY - timedelta(days=600)).isoformat()}, "older than 18 months"),
])
def test_non_comparable_evidence_does_not_count(postings, run_json, bad, reason):
    posting = postings["A-100"]
    ids = add(run_json, posting, report(), report(url="https://example.test/s/2", **bad))
    code, out, _ = suggest(run_json, posting, ids)
    assert code == 1
    excluded = out["error"]["details"]["excluded"]
    assert any(reason in p for p in excluded[0]["problems"])


def test_yearly_figures_become_monthly(searchable, postings, run_json):
    ids = add(run_json, postings["A-100"], report(period="year", amount_min=168000,
                                                  amount_max=192000))
    with db.session(searchable) as conn:
        item = salary.evidence(conn, ids[0])
    assert (item["amount_min"], item["amount_max"]) == (14000, 16000)


@pytest.mark.parametrize("bad", [
    {"url": "not a link"}, {"currency": "soles"}, {"period": "hour"},
    {"amount_min": 20000, "amount_max": 10000},
    {"observed_on": (TODAY + timedelta(days=3)).isoformat()},
])
def test_invalid_evidence_is_rejected(postings, run_json, bad):
    code, _, _ = run_json("salary", "evidence", "add",
                          data=[{**report(**bad), "posting_id": postings["A-100"]}])
    assert code == 1


def test_criteria_cannot_change_the_postings_country(postings, run_json):
    posting = postings["A-100"]
    ids = add(run_json, posting, report(), report(url="https://example.test/s/2"))
    code, out, _ = suggest(run_json, posting, ids, country="CL")
    assert code == 1 and "posting's country" in out["error"]["message"]


def test_no_data_is_explicit_with_what_was_checked(searchable, postings, cli):
    posting = postings["A-100"]
    code, out, _ = cli("salary", "none", str(posting), "--checked", "Example Salaries: none",
                       "--checked", "Company reviews: one report, other level")
    assert code == 0
    assert out["salary"]["status"] == "no_data"
    assert out["salary"]["amount"] is None
    assert len(out["salary"]["checked"]) == 2


def test_second_posting_at_the_same_company_reuses_evidence(searchable, postings, run_json,
                                                           cli, tmp_path):
    first = postings["A-100"]
    ids = add(run_json, first, report(), report(url="https://example.test/s/2"))
    suggest(run_json, first, ids)
    # The same job, found on another site in a later search.
    path = tmp_path / "later.json"
    later = [{**captures()[0], "provider": "beta", "external_id": "B-900",
              "url": "https://example.test/beta/aviso/900"}]
    path.write_text(json.dumps(later), encoding="utf-8")
    _, run, _ = cli("run", "start")
    _, imported, _ = cli("postings", "import", str(run["run_id"]), str(path))
    second = imported["postings"][0]["posting_id"]
    code, found, _ = cli("salary", "lookup", str(second))
    assert code == 0 and sorted(e["id"] for e in found["evidence"]["market"]) == sorted(ids)
    assert sorted(found["comparable_evidence_ids"]) == sorted(ids)
    _, out, _ = run_json("salary", "set", str(second), data={
        "evidence_ids": found["comparable_evidence_ids"], "criteria": {"currency": "PEN"},
        "reused": True, "note": "Reused the reports found for the same job."})
    assert out["salary"]["amount"] == 15000
    with db.session(searchable) as conn:
        outcomes = [r[0] for r in conn.execute(
            "SELECT outcome FROM salary_research_log WHERE posting_id = ?", (second,))]
    assert outcomes == ["reused"]


def test_lookup_reports_recent_research_without_data(postings, cli):
    posting = postings["A-100"]
    cli("salary", "none", str(posting), "--checked", "Example Salaries: none")
    _, found, _ = cli("salary", "lookup", str(posting))
    assert found["recently_without_data"] is True
    assert found["research"][0]["checked"] == ["Example Salaries: none"]
