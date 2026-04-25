"""
M-A1 Market Sizing algoritmiga unit testlar.

Faqat sof matematik mantiqni tekshiradi — DB yo'q, agent yo'q.
"""

from decimal import Decimal

import pytest

from app.algorithms.market_sizing import (
    MarketSizingInput,
    _data_confidence,
    run_market_sizing,
)


def _make_input(**overrides) -> MarketSizingInput:
    defaults = dict(
        tam_transactions_uzs=Decimal("12_000_000_000"),  # 12 mlrd
        sam_transactions_uzs=Decimal("1_200_000_000"),   # 1.2 mlrd
        competitor_count_city=20,
        competitor_count_radius=4,
        avg_monthly_revenue_uzs=Decimal("50_000_000"),   # 50 mln/oy
        median_monthly_revenue_uzs=Decimal("40_000_000"),
        annual_growth_rate_pct=0.08,
        gross_margin_pct=0.30,
        transaction_sample_size=1_500,
        quality_factor=1.0,
    )
    defaults.update(overrides)
    return MarketSizingInput(**defaults)


class TestDataConfidence:
    def test_large_sample_high_confidence(self):
        assert _data_confidence(15_000) == 0.95

    def test_medium_sample(self):
        assert _data_confidence(500) == 0.60

    def test_tiny_sample_low_confidence(self):
        assert _data_confidence(3) == 0.20

    def test_boundary_1000(self):
        assert _data_confidence(1_000) == 0.80

    def test_boundary_10000(self):
        assert _data_confidence(10_000) == 0.95


class TestRunMarketSizing:
    def test_tam_positive(self):
        result = run_market_sizing(_make_input())
        assert result.tam_uzs > 0

    def test_sam_less_than_tam(self):
        result = run_market_sizing(_make_input())
        assert result.sam_uzs <= result.tam_uzs

    def test_som_less_than_sam(self):
        result = run_market_sizing(_make_input())
        assert result.som_uzs <= result.sam_uzs

    def test_confidence_interval_ordering(self):
        result = run_market_sizing(_make_input())
        assert result.tam_low_uzs < result.tam_uzs < result.tam_high_uzs
        assert result.sam_low_uzs < result.sam_uzs < result.sam_high_uzs
        assert result.som_low_uzs < result.som_uzs < result.som_high_uzs

    def test_som_low_non_negative(self):
        result = run_market_sizing(_make_input())
        assert result.som_low_uzs >= 0

    def test_confidence_score_range(self):
        result = run_market_sizing(_make_input())
        assert 0.0 <= result.confidence_score <= 1.0

    def test_market_share_pct_with_4_competitors(self):
        result = run_market_sizing(_make_input(competitor_count_radius=4))
        expected_share = 100 / 5  # 1/(4+1) × 100
        assert abs(result.market_share_pct - expected_share) < 0.01

    def test_no_transaction_data_uses_benchmark(self):
        """Tranzaksiya ma'lumoti bo'lmaganda benchmark ishlatilishi."""
        result = run_market_sizing(
            _make_input(
                tam_transactions_uzs=Decimal(0),
                sam_transactions_uzs=Decimal(0),
                transaction_sample_size=0,
            )
        )
        # Bottom-up: 20 raqobatchi × 50mln × 12 = 12 mlrd
        expected_tam_bottom_up = Decimal("12_000_000_000")
        # w=0.20 (sample_size=0 → 0.20), so tam = 0.20×0 + 0.80×12mlrd = 9.6 mlrd
        assert result.tam_uzs > 0

    def test_no_competitors_reduces_confidence(self):
        no_comp = run_market_sizing(
            _make_input(competitor_count_city=0, competitor_count_radius=0)
        )
        with_comp = run_market_sizing(_make_input())
        assert no_comp.confidence_score < with_comp.confidence_score

    def test_quality_factor_scales_som(self):
        base = run_market_sizing(_make_input(quality_factor=1.0))
        boosted = run_market_sizing(_make_input(quality_factor=1.5))
        assert abs(float(boosted.som_uzs) / float(base.som_uzs) - 1.5) < 0.001

    def test_methodology_notes_present(self):
        result = run_market_sizing(_make_input())
        assert "tam_bottom_up_uzs" in result.methodology_notes
        assert "bayesian_weight_top_down" in result.methodology_notes

    def test_data_weight_reflects_sample_size(self):
        small = run_market_sizing(_make_input(transaction_sample_size=5))
        large = run_market_sizing(_make_input(transaction_sample_size=50_000))
        assert small.data_weight < large.data_weight

    def test_growth_rate_preserved(self):
        result = run_market_sizing(_make_input(annual_growth_rate_pct=0.15))
        assert result.market_growth_rate_pct == 0.15

    def test_gross_margin_preserved(self):
        result = run_market_sizing(_make_input(gross_margin_pct=0.45))
        assert result.gross_margin_pct == 0.45
