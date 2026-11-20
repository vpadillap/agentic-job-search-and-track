"""The /job-search skill: its commands exist, and its Spanish alias installs."""
from __future__ import annotations

import re
from pathlib import Path

from jobtracker.cli.main import build_parser
from jobtracker.core import skills
from tests.test_setup import _subcommands

SKILL = Path(__file__).resolve().parents[1] / ".claude" / "skills" / "job-search"


def test_skill_files_exist():
    assert {p.name for p in SKILL.glob("*.md")} == {
        "SKILL.md", "scoring-guide.md", "salary-guide.md", "batch-worker.md"}


def test_skill_only_uses_commands_that_exist():
    found = set()
    for path in SKILL.glob("*.md"):
        found |= set(re.findall(r"`jt ([a-z]+(?: [a-z-]+)?(?: [a-z-]+)?)",
                                path.read_text(encoding="utf-8")))
    top_level = _subcommands(build_parser())
    checked = set()
    for command in found:
        choices = top_level
        for word in command.split():
            if choices is None:
                break
            assert word in choices, f"`{command}` is not a jobtracker command"
            checked.add(word)
            choices = _subcommands(choices[word])
    assert {"context", "run", "start", "provider", "finish", "postings", "import", "list",
            "filter", "flag", "score", "set", "salary", "lookup", "evidence", "add",
            "none"} <= checked


def test_skill_states_the_read_only_rule():
    text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    assert "Never apply" in text and "providers/<id>.md" in text


def test_spanish_alias_installs_now_that_the_skill_exists(workspace, cli, skills_target):
    _, out, _ = cli("config", "set", "language", "es")
    assert "buscar-empleos" in out["skills"]["installed"]
    assert (skills_target / "buscar-empleos" / "SKILL.md").is_file()
    listed = {c["id"]: c for c in skills.command_list("es")}
    assert listed["job-search"]["available"] is True
    assert listed["job-search"]["example"] == "/buscar-empleos dias=7"


def test_skill_explains_the_work_mode_and_its_detail():
    text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    assert "`work_mode_detail`" in text
    assert "reading the title and the complete description" in text
    assert "`jt postings work-mode" in text
    worker = " ".join((SKILL / "batch-worker.md").read_text(encoding="utf-8").split())
    assert ("A posting that never says it is remote is treated as having some on-site"
            " presence") in worker
    assert "Its `work_mode` stays as captured" in worker


def test_skill_explains_how_to_turn_a_site_on_without_doing_it():
    text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    assert "job sites start switched off" in text
    assert "Never turn\na site on yourself" in text


# ── results during the search (job-search-live-results) ──────────────────

def test_skill_scores_batches_while_searching_with_a_cap():
    text = " ".join((SKILL / "SKILL.md").read_text(encoding="utf-8").split())
    assert "steps 3 and 4 run together" in text
    assert "At most 3 helpers at the same time" in text
    assert "up to 25 postings in all" in text
    assert "At most one salary helper at a time, counted in the 3" in text.replace("**", "")
    assert ".claude/skills/job-search/batch-worker.md" in text


def test_learning_is_refreshed_once_before_the_search():
    text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    refresh = text.index("## 2b. Refresh learning once")
    assert refresh < text.index("## 3. Search each provider") < text.index("## 4. Filter, score")
    assert text.count("`jt learning refresh`") == 1
    worker = (SKILL / "batch-worker.md").read_text(encoding="utf-8")
    assert "Do not run `jt learning refresh` without `--posting`" in worker


def test_skill_has_a_fallback_without_background_helpers():
    text = " ".join((SKILL / "SKILL.md").read_text(encoding="utf-8").split())
    assert "Without background helpers" in text
    assert "Right after each import, follow `batch-worker.md`" in text


def test_a_cool_down_does_not_hold_up_the_search():
    text = " ".join((SKILL / "SKILL.md").read_text(encoding="utf-8").split())
    assert "a cool-down never holds up the rest of the search" in text


def test_run_is_finished_only_after_every_batch():
    text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    before, finish = text.index("## 5. Before finishing"), text.index("## 6. Finish and report")
    assert before < finish
    assert "Wait until the queue is empty and no helper is running" in text[before:finish]


def test_helpers_never_search_or_finish_the_run():
    worker = " ".join((SKILL / "batch-worker.md").read_text(encoding="utf-8").split())
    assert "Never search or open a job site" in worker
    assert "never start or finish a run" in worker
    assert "never start helpers of your own" in worker


# ── location filter and restored postings (job-search-location-filter) ────

def _worker() -> str:
    return " ".join((SKILL / "batch-worker.md").read_text(encoding="utf-8").split())


def test_remote_only_profiles_filter_postings_that_do_not_say_remote():
    assert ("the profile accepts remote only and the posting does not say it is remote"
            in _worker())


def test_places_are_compared_by_meaning():
    worker = _worker()
    assert "A district or neighbourhood belongs to its city" in worker
    assert '"San Isidro, Lima"' in worker
    assert "A region or province that shares a city's name is not that city" in worker
    assert '"Huaral, Lima"' in worker
    assert "naming the place in `detail`" in worker


def test_place_doubts_keep_the_posting_with_a_flag():
    worker = _worker()
    assert "When you cannot tell, keep it with a flag" in worker
    assert '"City not stated"' in worker and '"District not among yours"' in worker
    assert "A remote posting is never filtered out for its location" in worker


def test_restored_postings_are_never_filtered():
    worker = _worker()
    assert "`restored: true`" in worker and "never filter it" in worker
    guide = (SKILL / "scoring-guide.md").read_text(encoding="utf-8")
    assert "place doubt" in guide
