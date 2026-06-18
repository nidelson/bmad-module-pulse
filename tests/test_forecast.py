"""Invariant tests for the v0.8 'predictability to price' forecast.

The forecast (BCP × h/BCP ± CI90%) is computed by the agent following the
dashboard instructions (no Python compute layer), so these pin the math and the
read-only/passive contract so a future edit cannot regress them.

Phase 1 scope: the forecast aggregation + backlog enumeration. The render
(Phase 2), the digest artifact (Phase 3) and the consolidating read-only
contract (Phase 5) get their own invariants when they land.
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).parents[1]
DASHBOARD = REPO_ROOT / "skills/bmad-pulse-dashboard/workflow.md"


def test_backlog_enumeration_defined():
    """The forecast input is the scored backlog: stories with bcp.total that
    have no pulse_metrics entry (not started), summed by category, read-only."""
    text = DASHBOARD.read_text()
    assert "Enumerate the scored backlog" in text
    assert "remaining_bcp_by_category" in text
    assert "no entry" in text.lower() and "pulse_metrics" in text
    assert "read-only" in text.lower()


def test_backlog_has_manual_total_fallback():
    """When story files can't be enumerated, a manual total is the fallback."""
    text = DASHBOARD.read_text()
    assert "pulse_forecast_remaining_bcp" in text
    assert "fall back" in text.lower()


def test_forecast_is_remaining_bcp_times_geo_hbcp():
    """Point forecast per category = remaining BCP × geometric h/BCP (reuses the
    v0.5 baseline, not a new metric)."""
    text = DASHBOARD.read_text()
    assert "remaining_bcp_cat × geo_mean(h_per_bcp_actual_cat)" in text
    assert "h_per_bcp_by_category" in text


def test_ci90_scales_band_to_k1645():
    """The 90% interval scales the v0.5 band from k=1 (~68%) to k=1.645 (~90%)
    via the sample GSD."""
    text = DASHBOARD.read_text()
    assert "k=1.645" in text
    assert "GSD_cat^1.645" in text
    assert "~68%" in text and "~90%" in text


def test_total_is_conservative_sum_with_stated_assumption():
    """The total interval sums per-category lows and highs — a conservative
    (correlated-errors) composition whose assumption must be stated."""
    text = DASHBOARD.read_text()
    assert "forecast_low_90 = Σ low_cat" in text
    assert "forecast_high_90 = Σ high_cat" in text
    assert "correlated" in text.lower() and "state this assumption" in text.lower()


def test_low_confidence_when_category_thin():
    """A category with n<3 falls back to the pooled baseline and flags the
    forecast low-confidence — no false precision on thin data."""
    text = DASHBOARD.read_text()
    assert "n < 3" in text
    assert "pooled" in text.lower() and "low-confidence" in text.lower()


def test_forecast_is_read_only():
    """The forecast never writes the backlog, the baseline, or any estimate."""
    text = DASHBOARD.read_text()
    assert "never writes the backlog, the baseline, or any estimate" in text


# --- Phase 2: forecast render (replaces the capacity forecast) --------------


def test_forecast_section_replaces_capacity_forecast():
    """The pre-0.8 leverage-extrapolation 'Previsão de Capacidade' is gone,
    replaced by the BCP-based 'Previsão de Projeto'."""
    text = DASHBOARD.read_text()
    assert "## 🔮 Previsão de Projeto" in text
    assert "## 🔮 Previsão de Capacidade" not in text, "old leverage forecast must be replaced"
    assert "Baseado no leverage médio de {avg}x" not in text


def test_forecast_section_shows_total_and_ci90():
    """The section must show the total hours and the 90% interval (PT-BR)."""
    text = DASHBOARD.read_text()
    assert "**Total: {forecast_total}h**" in text
    assert "[{forecast_low_90}–{forecast_high_90}]h (IC 90%)" in text


def test_forecast_section_has_per_category_table():
    """A per-category breakdown with remaining BCP, forecast band, confidence."""
    text = DASHBOARD.read_text()
    assert "| Categoria | BCP restante | Previsão (IC 90%) | Confiança |" in text
    assert "remaining_bcp_by_category" in text


def test_forecast_section_states_conservative_assumption():
    """The rendered note must state the conservative (correlated-errors) sum
    assumption and the low-confidence (pooled) handling."""
    text = DASHBOARD.read_text()
    assert "conservadora" in text and "correlacionados" in text
    assert "baixa confiança" in text.lower()


def test_forecast_section_gated_on_nonempty_backlog():
    """An empty backlog → no section (gated on remaining BCP, not just the flag)."""
    text = DASHBOARD.read_text()
    assert "AND the scored backlog has remaining BCP" in text or "AND forecast is non-empty" in text


# --- Phase 3: thin digest delivery ------------------------------------------


def test_digest_artifact_generated():
    """A concise digest.md is generated with forecast, predictability and
    drifting cohorts."""
    text = DASHBOARD.read_text()
    assert "digest.md" in text
    assert "PULSE digest" in text
    assert "Previsão de Projeto" in text and "Previsibilidade" in text


def test_digest_is_generated_only_no_direct_api():
    """Thin delivery invariant: PULSE generates the artifact but never calls
    Slack/Linear (or any external) API directly."""
    text = DASHBOARD.read_text()
    assert "never calls any external API itself" in text
    assert "never calls Slack/Linear" in text
    assert "generated only" in text.lower()


def test_digest_delivery_delegated_to_on_complete():
    """Delivery is delegated to the user-configured on_complete command, with a
    documented webhook example — the channel/credentials are the user's."""
    text = DASHBOARD.read_text()
    assert "on_complete" in text
    assert "PULSE_SLACK_WEBHOOK" in text
    assert "never in PULSE" in text


# --- Phase 5: passive/read-only contract (consolidating lock) ---------------


def test_forecast_passive_invariant_note_present():
    """The 'why' must live next to the code: a forecast passive invariant note
    (read-only, does not drive estimation, no direct external API)."""
    text = DASHBOARD.read_text()
    assert "Forecast passive invariant" in text
    assert "read-only and passive" in text
    assert "does not drive estimation" in text


def test_forecast_never_mutates_estimate_baseline_or_backlog():
    """Consolidating lock: the v0.8 forecast/digest never write the story
    frontmatter, the BCP baseline, the backlog, or any estimate."""
    text = DASHBOARD.read_text()
    assert "never writes" in text
    assert "the BCP baseline, the backlog, or any estimate" in text


def test_forecast_backlog_read_is_zero_write_coupled():
    """Reading the scored backlog must not regress PULSE's zero-write stance:
    the enumeration is explicitly read-only over story files, and the recording
    workflows never write a forecast/baseline field."""
    assert "reads story files **read-only**" in DASHBOARD.read_text()
    # track-start/track-done own the recording; they must not gain forecast writes
    for wf in ("bmad-pulse-track-start", "bmad-pulse-track-done"):
        wf_text = (REPO_ROOT / f"skills/{wf}/workflow.md").read_text()
        assert "remaining_bcp" not in wf_text and "forecast_total" not in wf_text, (
            f"{wf} must not compute or persist forecast fields"
        )
