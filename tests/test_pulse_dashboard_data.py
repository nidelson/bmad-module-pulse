"""Tests for the dashboard data entry point (issue #111, final slice).

The point of this module is determinism, so the central test runs the same input
twice and demands byte-identical output — the property an LLM computing medians
cannot offer.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "skills/bmad-pulse-dashboard/scripts"
sys.path.insert(0, str(SCRIPTS))

from pulse_dashboard_data import (  # noqa: E402
    build_dashboard_data,
    parse_sprint_status,
    render_summary,
)

FIXTURE = """
pulse_metrics:
  1-1-primeira:
    category: backend
    actual_hours: 5.0
    estimated_hours: 5.0
    estimate_error_pct: 0.0
    first_pass: true
    review_cycles: 1
    dev_count: 1
    leverage_vs_reference: 10.0
    estimated_hours_reference: 50.0
    bcp_recorded:
      total: 10
      h_per_bcp_actual: 0.5
    process_health:
      flow_complete: true
      halts: 0
  1-2-segunda:
    category: backend
    actual_hours: 4.0
    estimated_hours: 5.0
    estimate_error_pct: 20.0
    first_pass: false
    review_cycles: 2
    dev_count: 1
    leverage_vs_reference: 20.0
    estimated_hours_reference: 50.0
    bcp_recorded:
      total: 10
      h_per_bcp_actual: 0.4
    process_health:
      flow_complete: true
      halts:
        - kind: approval_wait
          duration_min: 30
          pre_approved_batch: false
  1-3-terceira:
    category: backend
    actual_hours: 6.0
    estimated_hours: 5.0
    estimate_error_pct: 20.0
    first_pass: true
    review_cycles: 1
    dev_count: 1
    leverage_vs_reference: 40.0
    estimated_hours_reference: 50.0
    bcp_recorded:
      total: 10
      h_per_bcp_actual: 0.6
    process_health:
      flow_complete: true
      halts: 2
"""


@pytest.fixture
def data():
    return build_dashboard_data(parse_sprint_status(FIXTURE))


class TestParse:
    def test_reads_the_metrics_block(self):
        parsed = parse_sprint_status(FIXTURE)
        assert len(parsed["pulse_metrics"]) == 3

    def test_empty_input_is_an_empty_dict(self):
        assert parse_sprint_status("") == {}

    def test_missing_metrics_block_yields_zero_stories(self):
        out = build_dashboard_data({"other_key": 1})
        assert out["stories_measured"] == 0
        assert out["predictability"]["score"] is None


class TestBuildDashboardData:
    def test_every_section_is_present(self, data):
        assert set(data) == {
            "stories_measured", "predictability", "h_per_bcp",
            "leverage_vs_reference", "segment_split", "reference_regime",
            "process_health", "drift_watchlist", "forecast",
        }

    def test_predictability_from_hand_computed_values(self, data):
        """errors [0, 20, 20] → median 20 → score 80%."""
        assert data["predictability"]["score"] == pytest.approx(80.0)
        assert data["predictability"]["median_error_pct"] == pytest.approx(20.0)

    def test_h_per_bcp_geometric_mean(self, data):
        """geo_mean(0.5, 0.4, 0.6) = (0.12)^(1/3) ≈ 0.4932."""
        pooled = data["h_per_bcp"]["by_category"]["backend"]["pooled"]
        assert pooled["geo_mean"] == pytest.approx(0.12 ** (1 / 3), rel=1e-6)

    def test_first_pass_counts(self, data):
        fp = data["process_health"]["first_pass"]
        assert (fp["passed"], fp["total"]) == (2, 3)
        assert fp["rate"] == pytest.approx(200 / 3)

    def test_leverage_reports_both_centres(self, data):
        """mean(10,20,40) = 23.33 vs geo_mean = 20.0 — the gap stays visible."""
        lv = data["leverage_vs_reference"]
        assert lv["mean"] == pytest.approx(70 / 3)
        assert lv["geo_mean"] == pytest.approx(8000 ** (1 / 3))

    def test_single_reference_regime(self, data):
        """50/10 = 5.0 for all three."""
        assert data["reference_regime"]["single_regime"] is True

    def test_halts_across_shapes(self, data):
        """0 (int) + 1 (object) + 2 (int) = 3."""
        assert data["process_health"]["halts"]["total_halts"] == 3
        assert data["process_health"]["halts"]["approval_wait_minutes"] == 30.0

    def test_forecast_absent_without_a_backlog(self, data):
        assert data["forecast"]["status"] == "no_backlog"

    def test_forecast_present_when_backlog_given(self):
        out = build_dashboard_data(parse_sprint_status(FIXTURE), {"backend": 100})
        assert out["forecast"]["status"] == "ok"
        assert out["forecast"]["point"] == pytest.approx(100 * 0.12 ** (1 / 3), rel=1e-6)


class TestDeterminism:
    def test_same_input_gives_byte_identical_output(self):
        """The property the LLM could not offer — and the reason for this issue."""
        a = json.dumps(build_dashboard_data(parse_sprint_status(FIXTURE)), default=str, sort_keys=True)
        b = json.dumps(build_dashboard_data(parse_sprint_status(FIXTURE)), default=str, sort_keys=True)
        assert a == b

    def test_summary_is_stable_across_runs(self):
        data = build_dashboard_data(parse_sprint_status(FIXTURE))
        assert render_summary(data) == render_summary(data)


class TestRenderSummary:
    def test_missing_values_render_as_dash_not_zero(self):
        out = render_summary(build_dashboard_data({"pulse_metrics": {}}))
        assert "—" in out and "Stories medidas: 0" in out

    def test_flags_a_multiple_reference_regime(self):
        broken = FIXTURE.replace(
            "    estimated_hours_reference: 50.0\n    bcp_recorded:\n      total: 10\n      h_per_bcp_actual: 0.6",
            "    estimated_hours_reference: 90.0\n    bcp_recorded:\n      total: 10\n      h_per_bcp_actual: 0.6",
        )
        out = render_summary(build_dashboard_data(parse_sprint_status(broken)))
        assert "Regime de referência múltiplo" in out

    def test_healthy_drift_says_so_explicitly(self, data):
        assert "nenhuma coorte acima do limiar" in render_summary(data)


class TestCLI:
    def _run(self, tmp_path, *args):
        f = tmp_path / "sprint-status.yaml"
        f.write_text(FIXTURE, encoding="utf-8")
        return subprocess.run(
            [sys.executable, str(SCRIPTS / "pulse_dashboard_data.py"),
             "--sprint-status", str(f), *args],
            capture_output=True, text=True,
        )

    def test_exits_zero_and_prints_the_summary(self, tmp_path):
        r = self._run(tmp_path)
        assert r.returncode == 0
        assert "Previsibilidade: 80.0%" in r.stdout

    def test_json_mode_is_parseable(self, tmp_path):
        r = self._run(tmp_path, "--json")
        assert json.loads(r.stdout)["stories_measured"] == 3

    def test_missing_file_fails_loudly(self):
        r = subprocess.run(
            [sys.executable, str(SCRIPTS / "pulse_dashboard_data.py"),
             "--sprint-status", "/nonexistent/x.yaml"],
            capture_output=True, text=True,
        )
        assert r.returncode == 1 and "not found" in r.stderr

    def test_invalid_remaining_bcp_json_is_rejected(self, tmp_path):
        r = self._run(tmp_path, "--remaining-bcp", "{not json}")
        assert r.returncode == 1 and "not valid JSON" in r.stderr

    def test_cli_output_is_reproducible(self, tmp_path):
        """Two runs, byte-identical stdout."""
        assert self._run(tmp_path, "--json").stdout == self._run(tmp_path, "--json").stdout
