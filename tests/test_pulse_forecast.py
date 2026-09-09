"""Tests for forecast and drift detection (issue #111, slice 4).

Forecasting is where a dashboard is most tempted to lie, so most of these tests
defend a rule about HONESTY rather than about arithmetic: silence over false
alarms, band over point, low-confidence marked as such.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(
    0, str(Path(__file__).resolve().parents[1] / "skills/bmad-pulse-dashboard/scripts")
)

from pulse_aggregations import Story  # noqa: E402
from pulse_forecast import (  # noqa: E402
    COHORT_WINDOW,
    DRIFT_ALERT_THRESHOLD_PCT,
    capacity_forecast,
    cohort_drift,
    cohort_key,
    drift_watchlist,
)


def story(key="s", category="backend", hours=1.0, h_per_bcp=0.1, total=10, err=None):
    raw = {"category": category, "actual_hours": hours,
           "bcp_recorded": {"total": total, "h_per_bcp_actual": h_per_bcp}}
    if err is not None:
        raw["estimate_error_pct"] = err
    return Story(key, raw)


class TestCohortKey:
    def test_bcp_story_keys_on_category_and_segment(self):
        assert cohort_key(story(total=2), 10.0) == ("backend", "micro")
        assert cohort_key(story(total=50), 10.0) == ("backend", "story")

    def test_non_bcp_project_falls_back_to_category_alone(self):
        """Without this, non-BCP projects collapse into one meaningless bucket."""
        assert cohort_key(Story("a", {"category": "web"}), None) == ("web",)


class TestCohortDrift:
    def test_stays_silent_below_three_samples(self):
        """Drift from 1-2 stories is owned by its outlier."""
        stories = [story("a", err=80.0), story("b", err=90.0)]
        out = cohort_drift(stories, ("backend", "story"))
        assert out["status"] == "insufficient"
        assert out["median_abs_drift_pct"] is None

    def test_median_over_the_recent_window(self):
        """Window = last 5 of 8 → [500, 500, 10, 20, 30], sorted median = 30.0.

        The two surviving 500s sit above the median and cannot drag it — which
        is the whole reason this is a median and not a mean (mean = 212.0).
        """
        stories = [story(f"old{i}", err=500.0) for i in range(5)]
        stories += [story(f"s{i}", err=e) for i, e in enumerate([10.0, 20.0, 30.0])]
        out = cohort_drift(stories, ("backend", "story"))
        assert out["n"] == COHORT_WINDOW
        assert out["median_abs_drift_pct"] == pytest.approx(30.0)
        assert sum([500, 500, 10, 20, 30]) / 5 == 212.0  # what a mean would say

    def test_window_forgets_old_stories(self):
        """A baseline that never forgets cannot see a team improve."""
        stories = [story(f"bad{i}", err=200.0) for i in range(10)]
        stories += [story(f"good{i}", err=5.0) for i in range(5)]
        out = cohort_drift(stories, ("backend", "story"))
        assert out["median_abs_drift_pct"] == 5.0  # only the last 5 count

    def test_reports_which_stories_it_used(self):
        stories = [story(f"s{i}", err=10.0) for i in range(3)]
        assert cohort_drift(stories, ("backend", "story"))["sample_story_ids"] == ["s0", "s1", "s2"]


class TestDriftWatchlist:
    def test_healthy_cohorts_are_omitted(self):
        """An empty list is the healthy default, not missing data."""
        stories = [story(f"s{i}", err=5.0) for i in range(4)]
        assert drift_watchlist(stories) == []

    def test_flags_a_drifting_cohort(self):
        stories = [story(f"s{i}", err=60.0) for i in range(4)]
        out = drift_watchlist(stories)
        assert len(out) == 1
        assert out[0]["median_abs_drift_pct"] == 60.0
        assert out[0]["label"] == "backend / story"

    def test_threshold_is_25_percent(self):
        below = [story(f"s{i}", err=24.0) for i in range(4)]
        above = [story(f"s{i}", err=26.0) for i in range(4)]
        assert drift_watchlist(below) == []
        assert len(drift_watchlist(above)) == 1
        assert DRIFT_ALERT_THRESHOLD_PCT == 25.0

    def test_sorted_worst_first(self):
        stories = [story(f"b{i}", category="backend", err=40.0) for i in range(4)]
        stories += [story(f"f{i}", category="frontend", err=90.0) for i in range(4)]
        out = drift_watchlist(stories)
        assert [e["cohort"][0] for e in out] == ["frontend", "backend"]

    def test_thin_cohort_never_raises_a_false_alarm(self):
        """2 terrible stories must not trigger an alert."""
        stories = [story(f"s{i}", err=900.0) for i in range(2)]
        assert drift_watchlist(stories) == []


class TestCapacityForecast:
    def _measured(self, n=4, h_per_bcp=0.5, category="backend"):
        return [story(f"m{i}", category=category, hours=5.0,
                      h_per_bcp=h_per_bcp, total=10) for i in range(n)]

    def test_point_and_band_from_the_category_baseline(self):
        """100 BCP × 0.5 h/BCP = 50h, with a band around it."""
        out = capacity_forecast(self._measured(), {"backend": 100})
        assert out["point"] == pytest.approx(50.0)
        assert out["low_90"] <= out["point"] <= out["high_90"]
        assert out["by_category"]["backend"]["confidence"] == "ok"

    def test_band_is_led_not_the_point(self):
        """The point looks precise; the interval is the honest answer."""
        out = capacity_forecast(self._measured(), {"backend": 100})
        assert out["lead_with"] == "band"

    def test_thin_category_uses_pooled_and_is_marked_low_confidence(self):
        stories = self._measured(n=4, category="backend")
        out = capacity_forecast(stories, {"mobile": 50})
        assert out["by_category"]["mobile"]["confidence"] == "baixa (pooled)"
        assert out["pooled_pct"] == 100.0
        assert out["precision"] == "baixa"

    def test_precision_thresholds(self):
        """>50% pooled → baixa; >20% → média; else alta."""
        stories = self._measured(n=4, category="backend")
        alta = capacity_forecast(stories, {"backend": 100, "mobile": 10})
        media = capacity_forecast(stories, {"backend": 100, "mobile": 30})
        baixa = capacity_forecast(stories, {"backend": 10, "mobile": 100})
        assert (alta["precision"], media["precision"], baixa["precision"]) == ("alta", "média", "baixa")

    def test_total_band_sums_bounds_conservatively(self):
        """Summing bounds assumes correlated errors — the wider, honest choice."""
        stories = self._measured(n=4)
        out = capacity_forecast(stories, {"backend": 50, "frontend": 50})
        cats = out["by_category"]
        assert out["low_90"] == pytest.approx(cats["backend"]["low_90"] + cats["frontend"]["low_90"])
        assert out["high_90"] == pytest.approx(cats["backend"]["high_90"] + cats["frontend"]["high_90"])

    def test_empty_backlog_is_no_forecast_not_zero_hours(self):
        out = capacity_forecast(self._measured(), {})
        assert out["status"] == "no_backlog" and out["point"] is None

    def test_no_baseline_declines_to_guess(self):
        """No measured story means no factor — refuse rather than invent one."""
        out = capacity_forecast([], {"backend": 100})
        assert out["status"] == "no_baseline" and out["point"] is None

    def test_ignores_malformed_backlog_entries(self):
        out = capacity_forecast(self._measured(), {"backend": 100, "bad": "x",
                                                   "neg": -5, "zero": 0, "flag": True})
        assert list(out["by_category"]) == ["backend"]

    def test_effort_floor_excluded_from_the_forecast_factor(self):
        """A 2-minute story would drag the factor toward zero.

        Covers BOTH paths, because they read different factors: the category
        path inherits the floor from `h_per_bcp_by_category`, while the pooled
        fallback computes its own ratios and must apply the floor itself. A
        sabotage that removed the floor only from the pooled path passed until
        this second assertion existed.
        """
        stories = self._measured(n=4, h_per_bcp=0.5)
        stories.append(story("tiny", hours=0.01, h_per_bcp=0.001, total=1))

        own = capacity_forecast(stories, {"backend": 100})
        assert own["point"] == pytest.approx(50.0)

        # `mobile` has no baseline → pooled factor, which must also be floored.
        pooled = capacity_forecast(stories, {"mobile": 100})
        assert pooled["by_category"]["mobile"]["confidence"] == "baixa (pooled)"
        assert pooled["point"] == pytest.approx(50.0)
