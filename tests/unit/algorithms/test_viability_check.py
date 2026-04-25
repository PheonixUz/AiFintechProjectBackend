"""M-D1 Viability Check algoritmiga unit testlar."""

from decimal import Decimal

import pytest

from app.algorithms.viability_check import ViabilityModelInput, run_viability_check


def _input(**overrides) -> ViabilityModelInput:
    data = {
        "initial_capital_uzs": Decimal("420000000"),
        "startup_capex_uzs": Decimal("210000000"),
        "expected_monthly_revenue_uzs": Decimal("110000000"),
        "gross_margin_pct": 0.36,
        "variable_cost_pct": 0.64,
        "monthly_fixed_cost_uzs": Decimal("24000000"),
        "monthly_loan_payment_uzs": Decimal("6500000"),
        "owner_draw_uzs": Decimal("7000000"),
        "simulation_months": 24,
        "monte_carlo_iterations": 1000,
        "random_seed": 123,
    }
    data.update(overrides)
    return ViabilityModelInput(**data)


def test_viability_returns_monthly_cashflow():
    result = run_viability_check(_input())

    assert len(result.months) == 24
    assert result.months[0].month_index == 1
    assert result.months[-1].month_index == 24
    assert 0 <= result.survival_probability_24m <= 1
    assert result.recommendation in {"approve", "review", "reject"}


def test_viability_is_deterministic_with_seed():
    first = run_viability_check(_input(random_seed=99))
    second = run_viability_check(_input(random_seed=99))

    assert first.viability_score == second.viability_score
    assert first.median_final_cash_uzs == second.median_final_cash_uzs
    assert first.months[0].expected_revenue_uzs == second.months[0].expected_revenue_uzs


def test_weak_plan_has_lower_score_than_strong_plan():
    weak = run_viability_check(
        _input(
            initial_capital_uzs=Decimal("120000000"),
            expected_monthly_revenue_uzs=Decimal("45000000"),
            monthly_fixed_cost_uzs=Decimal("36000000"),
            random_seed=7,
        )
    )
    strong = run_viability_check(
        _input(
            initial_capital_uzs=Decimal("600000000"),
            expected_monthly_revenue_uzs=Decimal("150000000"),
            monthly_fixed_cost_uzs=Decimal("22000000"),
            random_seed=7,
        )
    )

    assert strong.viability_score > weak.viability_score
    assert strong.survival_probability_24m > weak.survival_probability_24m


def test_invalid_revenue_raises():
    with pytest.raises(ValueError):
        run_viability_check(_input(expected_monthly_revenue_uzs=Decimal("0")))
