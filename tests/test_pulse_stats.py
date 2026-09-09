"""Tests for the deterministic statistical core (issue #111).

The expected values here are computed by hand or from an independent identity —
never by calling the function under test and pasting what it printed. A test
written that way passes against a wrong implementation.
"""

import math
import sys
from pathlib import Path

import pytest

sys.path.insert(
    0, str(Path(__file__).resolve().parents[1] / "skills/bmad-pulse-dashboard/scripts")
)

from pulse_stats import (  # noqa: E402
    K_90,
    MIN_N_FOR_DISPERSION,
    clamped_error_to_accuracy,
    confidence_band,
    geometric_mean,
    geometric_sd,
    half_split_direction,
    median,
)


class TestGeometricMean:
    def test_perfect_reciprocals_average_to_one(self):
        """The property that makes the geometric mean the right choice.

        A story at 2x and one at 0.5x cancel. The arithmetic mean would say
        1.25x — biased upward, which is exactly how a leverage metric ends up
        flattering itself.
        """
        assert geometric_mean([2.0, 0.5]) == pytest.approx(1.0)
        assert sum([2.0, 0.5]) / 2 == 1.25  # what we are NOT doing

    def test_known_value_by_hand(self):
        """geo_mean(1, 2, 4) = (1*2*4)^(1/3) = 8^(1/3) = 2."""
        assert geometric_mean([1.0, 2.0, 4.0]) == pytest.approx(2.0)

    def test_resists_the_outlier_that_drags_the_arithmetic_mean(self):
        xs = [1.0, 1.0, 1.0, 1.0, 100.0]
        assert geometric_mean(xs) == pytest.approx(100 ** (1 / 5))  # ~2.51
        assert sum(xs) / len(xs) == 20.8  # the baseline this would have written

    def test_empty_is_none_not_zero(self):
        """`0.0` would render as a real measurement of zero cost."""
        assert geometric_mean([]) is None

    def test_no_overflow_on_large_products(self):
        """`(prod)^(1/n)` overflows here; the log-space form does not."""
        assert geometric_mean([1e300, 1e300]) == pytest.approx(1e300)

    @pytest.mark.parametrize("bad", [0.0, -1.0, float("nan"), float("inf")])
    def test_rejects_non_positive_instead_of_skipping(self, bad):
        """Design rule 4: a bad ratio is an upstream defect, not noise."""
        with pytest.raises(ValueError, match="positive finite ratio"):
            geometric_mean([1.0, 2.0, bad])


class TestGeometricSD:
    def test_identical_values_have_no_spread(self):
        assert geometric_sd([3.0, 3.0, 3.0]) == pytest.approx(1.0)

    def test_uses_sample_denominator_not_population(self):
        """The n-1 choice is verifiable, not stylistic.

        For [1, 2, 4] the logs are [0, ln2, 2ln2]. Sample variance uses n-1=2:
            mean_log = ln2
            SS = (ln2)^2 + 0 + (ln2)^2 = 2(ln2)^2
            var = 2(ln2)^2 / 2 = (ln2)^2   →  sd = ln2  →  GSD = 2
        Population (n=3) would give GSD = exp(ln2 * sqrt(2/3)) ≈ 1.74.
        """
        assert geometric_sd([1.0, 2.0, 4.0]) == pytest.approx(2.0)
        population = math.exp(math.log(2) * math.sqrt(2 / 3))
        assert geometric_sd([1.0, 2.0, 4.0]) != pytest.approx(population)

    def test_thin_sample_returns_none(self):
        """One degree of freedom is owned by its outlier — refuse to report."""
        assert geometric_sd([1.0, 2.0]) is None
        assert geometric_sd([1.0]) is None
        assert geometric_sd([]) is None
        assert geometric_sd([1.0, 2.0, 4.0]) is not None
        assert MIN_N_FOR_DISPERSION == 3


class TestConfidenceBand:
    def test_band_is_multiplicative_and_centred(self):
        """low * high == centre^2 — the signature of a log-space interval.

        An additive band would fail this and could put `low` below zero.
        """
        low, centre, high, n = confidence_band([1.0, 2.0, 4.0])
        assert low * high == pytest.approx(centre**2)
        assert low > 0
        assert (low, centre, high, n) == pytest.approx((1.0, 2.0, 4.0, 3))

    def test_ninety_percent_is_wider_than_typical(self):
        xs = [1.0, 2.0, 4.0, 8.0]
        typical = confidence_band(xs)
        ninety = confidence_band(xs, k=K_90)
        assert ninety[0] < typical[0] and ninety[2] > typical[2]
        assert K_90 == 1.645

    def test_thin_sample_yields_no_band(self):
        """A range that cannot be estimated must not be rendered as one."""
        assert confidence_band([1.0, 2.0]) is None


class TestMedian:
    def test_odd_and_even(self):
        assert median([3.0, 1.0, 2.0]) == 2.0
        assert median([1.0, 2.0, 3.0, 4.0]) == 2.5

    def test_empty_is_none(self):
        assert median([]) is None

    def test_resists_outlier_where_mean_does_not(self):
        xs = [1.0, 2.0, 3.0, 1000.0]
        assert median(xs) == 2.5
        assert sum(xs) / len(xs) == 251.5


class TestPredictability:
    def test_clamps_at_zero_instead_of_going_negative(self):
        """-50% predictable invites the wrong reading; 0 is the floor."""
        assert clamped_error_to_accuracy(150.0) == 0.0
        assert clamped_error_to_accuracy(324.0) == 0.0  # story 23.3, real value

    def test_exact_estimate_is_full_accuracy(self):
        assert clamped_error_to_accuracy(0.0) == 100.0

    def test_sign_of_error_does_not_matter(self):
        """Over- and under-estimating by the same amount is equally imprecise."""
        assert clamped_error_to_accuracy(-30.0) == clamped_error_to_accuracy(30.0)


class TestHalfSplitDirection:
    def test_falling_error_is_converging(self):
        assert half_split_direction([50.0, 40.0, 10.0, 5.0]) == "converging"

    def test_rising_error_is_diverging(self):
        """The real shape of the SIP dashboard: 32.4% → 53.5%."""
        assert half_split_direction([5.0, 10.0, 40.0, 50.0]) == "diverging"

    def test_small_change_is_stable_not_a_trend(self):
        """Without the tolerance, noise renders as an arrow every run."""
        assert half_split_direction([20.0, 21.0, 22.0, 23.0]) == "stable"

    def test_thin_sample_gives_no_arrow(self):
        assert half_split_direction([10.0, 50.0, 90.0]) == "insufficient"

    def test_odd_length_splits_without_overlapping_the_middle(self):
        """5 items → first 2 vs last 2; the middle story belongs to neither."""
        assert half_split_direction([10.0, 10.0, 999.0, 90.0, 90.0]) == "diverging"

    def test_absolute_value_is_applied_before_comparing(self):
        """A -60% error is as imprecise as +60%; direction must not cancel it."""
        assert half_split_direction([-60.0, -60.0, 5.0, 5.0]) == "converging"
