"""provider-throttling: the shared soft-block policy (readers/common.py), without any
site. Each reader's own tests cover how its answers map onto it."""
from __future__ import annotations

from datetime import UTC, datetime
from email.utils import format_datetime

import pytest

from jobtracker.core.readers import common

NOW = datetime(2026, 11, 19, 12, 0, tzinfo=UTC).timestamp()


@pytest.mark.parametrize("value, expected", [
    ("40", 40.0), (" 7 ", 7.0), ("0", 0.0), (None, None), ("", None), ("soon", None),
    (format_datetime(datetime(2026, 11, 19, 12, 2, tzinfo=UTC), usegmt=True), 120.0),
    (format_datetime(datetime(2026, 11, 19, 11, 0, tzinfo=UTC), usegmt=True), 0.0),
])
def test_retry_after_as_seconds_or_a_date(value, expected):
    assert common.parse_retry_after(value, NOW) == expected


@pytest.mark.parametrize("attempt, low, high", [(1, 10, 20), (2, 20, 40), (3, 40, 80),
                                                (5, 60, 120), (9, 60, 120)])
def test_backoff_with_equal_jitter(attempt, low, high):
    assert common.backoff(attempt, lambda: 0.0) == low
    assert common.backoff(attempt, lambda: 1.0) == high


@pytest.mark.parametrize("status, retry_after, soft", [
    (429, None, True), (999, None, True), (503, 30.0, True), (503, None, False),
    (403, None, False), (200, None, False)])
def test_soft_statuses(status, retry_after, soft):
    assert common.soft_status(status, retry_after) is soft


@pytest.mark.parametrize("title, challenge", [
    ("Just a moment...", True), ("Un momento…", True), ("Security | Glassdoor", True),
    ("Security Check - Indeed.com", True), ("Attention Required! | Cloudflare", False),
    ("Empleos | Bumeran Perú", False), (None, False)])
def test_challenge_pages(title, challenge):
    assert common.is_challenge(title) is challenge


class Clock:
    def __init__(self) -> None:
        self.now = NOW
        self.waits: list[float] = []

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.waits.append(seconds)
        self.now += seconds


def requests(*answers):
    """A request that throttles (with the given Retry-After) or returns a value."""
    queue = list(answers)

    def request():
        answer = queue.pop(0)
        if isinstance(answer, common.Throttle):
            raise answer
        return answer
    return request


def run(request, state=None, min_seconds=5):
    clock = Clock()
    state = {} if state is None else state
    result = common.attempt(request, state, min_seconds=min_seconds, clock=clock,
                            sleep=clock.sleep, rand=lambda: 0.5)
    return result, clock, state


def test_a_throttle_that_clears():
    result, clock, state = run(requests(common.Throttle("429"), "page"))
    assert result == "page" and clock.waits == [15.0] and state["retries"] == 1
    assert state["throttles"][0]["detail"] == "429"


def test_retry_after_wins_over_backoff_but_never_below_the_pacing():
    _, clock, _ = run(requests(common.Throttle("429", 40), common.Throttle("429", 1), "page"))
    assert clock.waits == [40, 5]


def test_three_attempts_then_a_cool_down():
    with pytest.raises(common.Stop) as stop:
        run(requests(*[common.Throttle("429")] * 3))
    assert stop.value.reason == "throttled"


def test_a_long_retry_after_is_a_cool_down_at_once():
    clock = Clock()
    with pytest.raises(common.Stop) as stop:
        common.attempt(requests(common.Throttle("429", 121)), {}, min_seconds=5, clock=clock,
                       sleep=clock.sleep)
    assert stop.value.retry_after == 121 and clock.waits == []


def test_the_run_budget():
    with pytest.raises(common.Stop):
        run(requests(common.Throttle("429"), "page"), state={"retries": common.RUN_RETRIES})


def test_the_throttle_log_is_bounded():
    state = {"throttles": [{"at": 0, "detail": "old"}] * common.THROTTLE_LOG}
    run(requests(common.Throttle("new"), "page"), state=state)
    assert len(state["throttles"]) == common.THROTTLE_LOG
    assert state["throttles"][-1]["detail"] == "new"
