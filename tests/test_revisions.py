"""Correcting what setup stored: titles in bulk, rules, and localized system rules."""
from __future__ import annotations

import io
import json

import pytest

from jobtracker.core import db, rules


@pytest.fixture
def send(cli, monkeypatch):
    def run(payload: object, *args: str):
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
        return cli(*args)

    return run


@pytest.fixture
def profiled(workspace, send):
    code, _, _ = send({"work_modes": ["remote"], "remote_scope": "region",
                       "remote_region": "Latin America",
                       "additional_facts": ["Knows Kafka from personal projects"]},
                      "profile", "set", "-")
    assert code == 0
    return workspace


def _titles(profile: dict) -> dict[str, dict]:
    return {item["title"]: item for item in profile["titles"]}


# ── profile fields added after the dry run ────────────────────────────────

def test_region_name_and_confirmed_facts_are_stored(profiled, cli):
    _, out, _ = cli("profile", "show")
    assert out["profile"]["remote_region"] == "Latin America"
    assert out["profile"]["additional_facts"] == ["Knows Kafka from personal projects"]


def test_an_earlier_answer_can_be_cleared_explicitly(profiled, send):
    _, out, _ = send({"remote_region": None, "additional_facts": []}, "profile", "set", "-")
    assert out["profile"]["remote_region"] is None
    assert out["profile"]["additional_facts"] == []
    assert out["profile"]["remote_scope"] == "region"  # not mentioned, so kept


# ── titles in bulk ────────────────────────────────────────────────────────

def test_several_titles_are_one_version(profiled, send):
    _, out, _ = send(
        [{"title": "Senior Data Engineer", "state": "included"},
         {"title": "Analytics Engineer", "state": "suggested", "reason": "same stack"},
         {"title": "ETL Developer", "state": "suggested", "reason": "look-alike"}],
        "profile", "titles", "-")
    assert out["profile"]["version"] == 2
    assert len(out["profile"]["titles"]) == 3

    _, out, _ = send(
        [{"title": "analytics engineer", "state": "included"},
         {"title": "ETL Developer", "state": "excluded"}],
        "profile", "titles", "-")
    assert out["profile"]["version"] == 3
    titles = _titles(out["profile"])
    assert titles["Analytics Engineer"] == {"title": "Analytics Engineer", "state": "included"}
    assert titles["ETL Developer"] == {"title": "ETL Developer", "state": "excluded"}


def test_a_reason_is_kept_while_the_state_is_unchanged(profiled, send, cli):
    send([{"title": "Data Architect", "state": "suggested", "reason": "seen twice"}],
         "profile", "titles", "-")
    _, out, _ = cli("profile", "title", "Data Architect", "suggested")
    assert _titles(out["profile"])["Data Architect"]["reason"] == "seen twice"
    _, out, _ = cli("profile", "title", "Data Architect", "excluded", "--reason", "too senior")
    assert _titles(out["profile"])["Data Architect"]["reason"] == "too senior"


def test_invalid_title_batch_stores_nothing(profiled, send, cli):
    code, out, _ = send(
        [{"title": "Data Engineer", "state": "included"},
         {"title": "BI Engineer", "state": "perhaps"}],
        "profile", "titles", "-")
    assert code == 1 and out["error"]["code"] == "invalid_profile"
    _, shown, _ = cli("profile", "show")
    assert shown["profile"]["version"] == 1 and shown["profile"]["titles"] == []


def test_titles_need_job_needs_first(workspace, send):
    code, out, _ = send([{"title": "Data Engineer", "state": "included"}],
                        "profile", "titles", "-")
    assert code == 1 and out["error"]["code"] == "no_profile"


def test_a_mistyped_title_can_be_removed(profiled, cli):
    cli("profile", "title", "Senoir Data Enginer", "included")
    _, out, _ = cli("profile", "remove-title", "senoir data enginer")
    assert out["profile"]["titles"] == []
    code, out, _ = cli("profile", "remove-title", "Never Added")
    assert code == 1 and out["error"]["code"] == "not_found"


# ── rules ─────────────────────────────────────────────────────────────────

def test_user_rule_can_be_reworded_and_retired(workspace, cli):
    _, added, _ = cli("rules", "add", "--text", "Knows Kafka", "--area", "resume")
    rule_id = str(added["rules"][0]["id"])

    _, edited, _ = cli("rules", "edit", rule_id, "--text", "No outsourcing consultancies")
    assert edited["rule"]["text"] == "No outsourcing consultancies"

    _, retired, _ = cli("rules", "retire", rule_id)
    assert retired["rule"]["status"] == "reverted"
    _, active, _ = cli("rules", "list")
    assert rule_id not in {str(r["id"]) for r in active["rules"]}
    _, everything, _ = cli("rules", "list", "--status", "all")
    assert rule_id in {str(r["id"]) for r in everything["rules"]}  # kept in history


def test_system_rules_cannot_be_changed_or_retired(workspace, cli):
    _, listed, _ = cli("rules", "list")
    system_id = str(next(r["id"] for r in listed["rules"] if r["origin"] == "system"))
    for command in (("rules", "edit", system_id, "--text", "anything goes"),
                    ("rules", "retire", system_id)):
        code, out, _ = cli(*command)
        assert code == 1 and out["error"]["code"] == "protected_rule"
    _, after, _ = cli("rules", "list")
    assert after["rules"] == listed["rules"]


def test_unknown_rule(workspace, cli):
    code, out, _ = cli("rules", "retire", "9999")
    assert code == 1 and out["error"]["code"] == "not_found"


def test_defaults_the_setup_skill_relies_on_are_system_rules(workspace, cli):
    _, out, _ = cli("rules", "list")
    keys = {rule["key"] for rule in out["rules"]}
    assert {"resume_layout_consent", "cover_letter_default"} <= keys


def test_system_rules_follow_the_panel_language(workspace, cli):
    _, english, _ = cli("rules", "list")
    cli("rules", "add", "--text", "Prefer product companies", "--area", "search")
    cli("config", "set", "language", "es")
    _, spanish, _ = cli("rules", "list")
    by_key = {r["key"]: r["text"] for r in spanish["rules"] if r["origin"] == "system"}
    assert by_key["no_auto_apply"].startswith("El agente nunca")
    assert set(by_key) == {r["key"] for r in english["rules"]}
    assert all(text != next(e["text"] for e in english["rules"] if e["key"] == key)
               for key, text in by_key.items())
    # The user's own words are never translated.
    assert "Prefer product companies" in [r["text"] for r in spanish["rules"]]
    _, context, _ = cli("context")
    assert context["rules"] == spanish["rules"]


def test_every_system_rule_has_a_spanish_text():
    assert {key for key, _, _ in rules.SYSTEM_RULES} == set(rules.SYSTEM_RULES_ES)


def test_changed_system_rule_text_is_refreshed_on_init(workspace, cli):
    with db.session(workspace) as conn:
        conn.execute("UPDATE rules SET text = 'old wording' WHERE key = 'no_auto_apply'")
    cli("init")
    _, out, _ = cli("rules", "list")
    text = next(r["text"] for r in out["rules"] if r["key"] == "no_auto_apply")
    assert text.startswith("The agent never")
    assert len([r for r in out["rules"] if r["key"] == "no_auto_apply"]) == 1


# ── messages name the command the user actually runs ──────────────────────

def test_messages_use_the_invoked_command_name(home, cli, monkeypatch):
    monkeypatch.setenv("JOBTRACKER_PROG", "python scripts/jt.py")
    _, out, _ = cli("rules", "list")
    assert "python scripts/jt.py init" in out["error"]["message"]
    _, out, _ = cli("profile", "title")
    assert "python scripts/jt.py profile title --help" in out["error"]["message"]
