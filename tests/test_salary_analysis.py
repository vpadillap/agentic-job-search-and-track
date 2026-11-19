"""rework-salary-research: everything available for the agent's analysis, the evidence
rule per kind of source, reuse by role and country, company profiles, and the reports
set aside. Fictional companies only."""
from __future__ import annotations

import json

import pytest

from jobtracker.core import applications, db, salary, tracking
from tests.test_salary import add, postings, report, run_json  # noqa: F401  (fixtures)
from tests.test_search import captures


@pytest.fixture
def target(postings, cli, tmp_path):  # noqa: F811
    """Another company's posting for the same role, level, and country as A-100."""
    record = {**captures()[0], "provider": "beta", "external_id": "B-950",
              "company": "Kuntur Seguros", "url": "https://example.test/beta/aviso/950"}
    path = tmp_path / "target.json"
    path.write_text(json.dumps([record]), encoding="utf-8")
    _, run, _ = cli("run", "start")
    _, imported, _ = cli("postings", "import", str(run["run_id"]), str(path))
    return imported["postings"][0]["posting_id"]


@pytest.fixture
def offer(searchable, postings):  # noqa: F811
    """Finlima S.A. offered the user 12,000 PEN a month (recorded on the application)."""
    with db.session(searchable) as conn:
        job = tracking.track(conn, [postings["A-101"]])[0]["job_id"]
        applications.update_details(conn, job, {
            "offered_salary": {"amount": 12000, "currency": "PEN", "basis": "gross"}})
    return job


def _set(run_json, posting_id, **data):  # noqa: F811
    body = {"criteria": {"currency": "PEN"}, "note": "Fictional note.", **data}
    return run_json("salary", "set", str(posting_id), data=body)


def test_lookup_gathers_offered_history_evidence_and_checks(  # noqa: F811
        target, searchable, postings, offer, cli, run_json):  # noqa: F811
    with db.session(searchable) as conn:
        salary.set_profile(conn, "Finlima S.A.", {
            "industry": "Banking", "size_band": "1,001-5,000 employees", "kind": "bank",
            "source": "Example Jobs company page", "source_url": "https://example.test/c/finlima"})
    _set(run_json, postings["A-100"], inputs=[{"kind": "offer", "application": offer}],
         checked=[{"source": "Example Salaries", "scope": "market", "found": False}])
    code, found, _ = cli("salary", "lookup", str(target))
    assert code == 0
    assert found["offered"] is None
    history = found["history"]
    assert history[0]["kind"] == "offer" and history[0]["application"] == offer
    assert history[0]["profile"]["industry"] == "Banking"
    assert history[0]["same_company"] is False
    # Same family, level, and country: what Example Salaries gave is known for this key.
    assert {"scope": "market", "source": "Example Salaries", "found": False} in [
        {k: c[k] for k in ("scope", "source", "found")} for c in found["checked"]]


def test_one_offer_from_a_similar_company_is_enough(target, searchable, postings, offer, run_json):  # noqa: F811
    code, out, _ = _set(run_json, target, range_min=11500, range_max=13500,
                        inputs=[{"kind": "offer", "application": offer}],
                        note="Close to what a similar bank offered you (1 offer, 2026).")
    assert code == 0, out
    stored = out["salary"]
    assert stored["counts"] == {"company": 0, "history": 1, "market": 0}
    assert stored["note"].startswith("Close to what a similar bank")
    assert (stored["range_min"], stored["range_max"]) == (11500, 13500)
    assert stored["inputs"][0]["application"] == offer


def test_one_company_reference_is_enough(target, postings, run_json):  # noqa: F811
    ids = add(run_json, target, report(scope="company", sample_size=7))
    code, out, _ = _set(run_json, target, inputs=[{"evidence_id": ids[0]}])
    assert code == 0, out
    assert out["salary"]["counts"] == {"company": 1, "history": 0, "market": 0}


def test_one_market_source_alone_is_refused(target, postings, run_json):  # noqa: F811
    ids = add(run_json, target, report())
    code, out, _ = _set(run_json, target, inputs=[{"evidence_id": ids[0]}])
    assert code == 1 and out["error"]["code"] == "insufficient_evidence"


def test_a_note_is_required_and_short(target, postings, run_json):  # noqa: F811
    ids = add(run_json, target, report(), report(url="https://example.test/s/2"))
    code, out, _ = _set(run_json, target, inputs=[{"evidence_id": i} for i in ids],
                        note="")
    assert code == 1 and "note" in out["error"]["message"]
    code, out, _ = _set(run_json, target, inputs=[{"evidence_id": i} for i in ids],
                        note="x" * 301)
    assert code == 1


def test_outlier_set_aside_is_recorded(target, postings, run_json):  # noqa: F811
    ids = add(run_json, target, report(scope="company", sample_size=5))
    code, out, _ = _set(run_json, target, inputs=[{"evidence_id": ids[0]}],
                        set_aside=[{"value": "45,000 PEN", "source": "Example Salaries",
                                    "reason": "three times the other four reports"}])
    assert code == 0
    assert out["salary"]["set_aside"] == [{"value": "45,000 PEN", "source": "Example Salaries",
                                           "reason": "three times the other four reports"}]


def test_market_evidence_is_reused_at_another_company(target, postings, cli, run_json):  # noqa: F811
    ids = add(run_json, postings["A-100"], report(), report(url="https://example.test/s/2"))
    _, found, _ = cli("salary", "lookup", str(target))   # Kallpa, same role
    assert sorted(e["id"] for e in found["evidence"]["market"]) == sorted(ids)
    assert found["evidence"]["company"] == []


def test_company_evidence_is_not_used_for_another_company(target, postings, cli, run_json):  # noqa: F811
    add(run_json, postings["A-100"], report(scope="company"))
    _, found, _ = cli("salary", "lookup", str(target))
    assert found["evidence"]["company"] == [] and found["evidence"]["market"] == []


def test_profile_keeps_its_source_and_unknown_fields(searchable, cli, run_json):  # noqa: F811
    code, out, _ = run_json("companies", "profile", "Kallpa Energía", data={
        "industry": "Energy", "size_band": "unknown", "source": "posting"})
    assert code == 0
    assert out["profile"] == {**out["profile"], "industry": "Energy", "size_band": None,
                              "source": "posting", "source_url": None}
    code, out, _ = run_json("companies", "profile", "Kallpa Energía", data={
        "kind": "utility", "source": "Example Jobs", "source_url": "not a link"})
    assert code == 1


def test_history_input_must_carry_a_salary(target, postings, run_json):  # noqa: F811
    code, out, _ = _set(run_json, target,
                        inputs=[{"kind": "published", "posting_id": postings["A-100"]}])
    assert code == 1 and "published salary" in out["error"]["message"]


def test_published_salaries_are_history(target, searchable, postings, cli):  # noqa: F811
    with db.session(searchable) as conn:
        conn.execute("UPDATE postings SET published_salary = ? WHERE id = ?",
                     (json.dumps({"min": 168000, "max": 192000, "currency": "PEN",
                                  "period": "year", "basis": "gross"}), postings["A-100"]))
    _, found, _ = cli("salary", "lookup", str(target))
    published = [h for h in found["history"] if h["kind"] == "published"]
    assert published[0]["amount_min"] == 14000 and published[0]["same_family"] is True
    _, own, _ = cli("salary", "lookup", str(postings["A-100"]))
    assert own["offered"] == {"min": 14000, "max": 16000, "currency": "PEN", "basis": "gross"}


def test_salary_form_currency_follows_the_posting_and_profile(workspace, cli, tmp_path):
    from jobtracker.core import applications as apps

    with db.session(workspace) as conn:
        assert apps.currency_hint(conn, {"country": "CL"}) == "CLP"
        assert apps.currency_hint(conn, {"country": "PE", "published_salary": {
            "min": 3000, "max": 4000, "currency": "USD"}}) == "USD"     # how this employer pays
        assert apps.currency_hint(conn, {"country": "ZZ"}) is None      # the user types it
    path = tmp_path / "p.json"
    path.write_text(json.dumps({"minimum_salary": {"amount": 4000, "currency": "EUR"}}),
                    encoding="utf-8")
    cli("profile", "set", str(path))
    with db.session(workspace) as conn:
        assert apps.currency_hint(conn, {"country": "CL"}) == "EUR"
