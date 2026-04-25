"""M-D1 Financial Viability Check algoritmi."""

from dataclasses import dataclass, field
from decimal import Decimal
from statistics import NormalDist

import numpy as np


@dataclass
class ViabilityModelInput:
    initial_capital_uzs: Decimal
    startup_capex_uzs: Decimal
    expected_monthly_revenue_uzs: Decimal
    gross_margin_pct: float
    variable_cost_pct: float
    monthly_fixed_cost_uzs: Decimal
    monthly_loan_payment_uzs: Decimal = Decimal("0")
    owner_draw_uzs: Decimal = Decimal("0")
    monthly_revenue_growth_pct: float = 0.0
    revenue_volatility_pct: float = 0.20
    annual_inflation_rate_pct: float = 0.12
    annual_macro_growth_pct: float = 0.03
    tax_rate_pct: float = 0.04
    simulation_months: int = 24
    monte_carlo_iterations: int = 2000
    seasonality_profile: dict[int, float] = field(default_factory=dict)
    competitor_count_radius: int = 0
    two_year_failure_rate_pct: float = 0.35
    clean_anomalies: bool = True
    random_seed: int | None = None


@dataclass
class ViabilityMonthResult:
    month_index: int
    expected_revenue_uzs: Decimal
    p10_revenue_uzs: Decimal
    p90_revenue_uzs: Decimal
    variable_cost_uzs: Decimal
    fixed_cost_uzs: Decimal
    loan_payment_uzs: Decimal
    tax_uzs: Decimal
    net_cashflow_uzs: Decimal
    cumulative_cash_p10_uzs: Decimal
    cumulative_cash_p50_uzs: Decimal
    cumulative_cash_p90_uzs: Decimal
    probability_negative_cash: float
    is_break_even_month: bool = False


@dataclass
class ViabilityModelResult:
    break_even_month: int | None
    runway_months: float
    survival_probability_24m: float
    cash_out_probability_24m: float
    probability_break_even_24m: float
    median_final_cash_uzs: Decimal
    p10_final_cash_uzs: Decimal
    p90_final_cash_uzs: Decimal
    worst_month_cash_uzs: Decimal
    min_required_capital_uzs: Decimal
    viability_score: float
    recommendation: str
    confidence_score: float
    methodology_notes: dict
    months: list[ViabilityMonthResult]


def _money(value: float | Decimal) -> Decimal:
    return Decimal(str(max(0.0, float(value)))).quantize(Decimal("0.01"))


def _signed_money(value: float | Decimal) -> Decimal:
    return Decimal(str(float(value))).quantize(Decimal("0.01"))


def _winsorize(
    values: np.ndarray, lower: float = 0.01, upper: float = 0.99
) -> np.ndarray:
    low, high = np.quantile(values, [lower, upper])
    return np.clip(values, low, high)


def _recommendation(score: float, survival: float, break_even_prob: float) -> str:
    if score >= 75 and survival >= 0.72 and break_even_prob >= 0.60:
        return "approve"
    if score >= 50 and survival >= 0.45:
        return "review"
    return "reject"


def run_viability_check(data: ViabilityModelInput) -> ViabilityModelResult:
    """Monte Carlo asosida break-even, runway va survival probability hisoblaydi."""
    if data.simulation_months < 1:
        raise ValueError("simulation_months musbat bo'lishi kerak")
    if data.monte_carlo_iterations < 100:
        raise ValueError("monte_carlo_iterations kamida 100 bo'lishi kerak")
    if data.expected_monthly_revenue_uzs <= 0:
        raise ValueError("expected_monthly_revenue_uzs musbat bo'lishi kerak")
    if data.initial_capital_uzs <= 0:
        raise ValueError("initial_capital_uzs musbat bo'lishi kerak")

    rng = np.random.default_rng(data.random_seed)
    iterations = data.monte_carlo_iterations
    months = data.simulation_months

    initial_cash = float(data.initial_capital_uzs - data.startup_capex_uzs)
    base_revenue = float(data.expected_monthly_revenue_uzs)
    fixed_cost = float(data.monthly_fixed_cost_uzs)
    loan_payment = float(data.monthly_loan_payment_uzs)
    owner_draw = float(data.owner_draw_uzs)
    monthly_inflation = (1 + data.annual_inflation_rate_pct) ** (1 / 12) - 1
    monthly_macro = (1 + data.annual_macro_growth_pct) ** (1 / 12) - 1
    monthly_growth = data.monthly_revenue_growth_pct + monthly_macro

    competitor_pressure = min(0.18, data.competitor_count_radius * 0.004)
    failure_prior = min(max(data.two_year_failure_rate_pct, 0.0), 0.95)
    volatility = max(0.01, data.revenue_volatility_pct)
    normal = NormalDist()

    cash_paths = np.full((iterations, months), initial_cash, dtype=float)
    revenue_paths = np.zeros((iterations, months), dtype=float)
    net_cashflow_paths = np.zeros((iterations, months), dtype=float)

    cumulative_cash = np.full(iterations, initial_cash, dtype=float)
    for month_idx in range(months):
        month_number = month_idx + 1
        seasonality = data.seasonality_profile.get((month_idx % 12) + 1, 1.0)
        trend = (1 + monthly_growth - competitor_pressure / 12) ** month_idx
        expected_revenue = max(0.0, base_revenue * trend * seasonality)

        sigma = volatility / 2.0
        mu = np.log(max(expected_revenue, 1.0)) - sigma**2 / 2
        monthly_revenue = rng.lognormal(mean=mu, sigma=sigma, size=iterations)
        if data.clean_anomalies:
            monthly_revenue = _winsorize(monthly_revenue)

        inflated_fixed_cost = fixed_cost * ((1 + monthly_inflation) ** month_idx)
        variable_cost = monthly_revenue * data.variable_cost_pct
        gross_profit = monthly_revenue - variable_cost
        tax = np.maximum(gross_profit - inflated_fixed_cost, 0) * data.tax_rate_pct
        net_cashflow = (
            monthly_revenue
            - variable_cost
            - inflated_fixed_cost
            - loan_payment
            - owner_draw
            - tax
        )
        cumulative_cash = cumulative_cash + net_cashflow

        revenue_paths[:, month_idx] = monthly_revenue
        net_cashflow_paths[:, month_idx] = net_cashflow
        cash_paths[:, month_idx] = cumulative_cash

    final_cash = cash_paths[:, -1]
    min_cash_with_initial = np.minimum(cash_paths.min(axis=1), initial_cash)
    survived = min_cash_with_initial >= 0
    survival_probability_raw = float(np.mean(survived))
    survival_probability = survival_probability_raw * (1 - failure_prior * 0.35)
    survival_probability = max(0.01, min(0.99, survival_probability))
    cash_out_probability = 1 - survival_probability

    first_negative = np.argmax(cash_paths < 0, axis=1) + 1
    never_negative = np.all(cash_paths >= 0, axis=1)
    if initial_cash < 0:
        runway_months = 0.0
    else:
        runway_months = float(
            np.median(np.where(never_negative, months, first_negative))
        )

    break_even_flags = net_cashflow_paths >= 0
    stable_break_even = np.zeros_like(break_even_flags, dtype=bool)
    for month_idx in range(months - 2):
        stable_break_even[:, month_idx] = np.all(
            break_even_flags[:, month_idx : month_idx + 3],
            axis=1,
        )
    first_break_even = np.argmax(stable_break_even, axis=1) + 1
    ever_break_even = np.any(stable_break_even, axis=1)
    break_even_paths = np.where(ever_break_even, first_break_even, months + 1)
    probability_break_even = float(np.mean(break_even_paths <= min(24, months)))
    break_even_month = (
        int(np.median(break_even_paths[break_even_paths <= months]))
        if np.any(break_even_paths <= months)
        else None
    )

    monthly_results: list[ViabilityMonthResult] = []
    for month_idx in range(months):
        month_number = month_idx + 1
        expected_revenue = float(np.median(revenue_paths[:, month_idx]))
        fixed_cost_month = fixed_cost * ((1 + monthly_inflation) ** month_idx)
        variable_cost_month = expected_revenue * data.variable_cost_pct
        tax_month = max(expected_revenue - variable_cost_month - fixed_cost_month, 0)
        tax_month *= data.tax_rate_pct
        net_cashflow_month = float(np.median(net_cashflow_paths[:, month_idx]))
        monthly_results.append(
            ViabilityMonthResult(
                month_index=month_number,
                expected_revenue_uzs=_money(expected_revenue),
                p10_revenue_uzs=_money(np.quantile(revenue_paths[:, month_idx], 0.10)),
                p90_revenue_uzs=_money(np.quantile(revenue_paths[:, month_idx], 0.90)),
                variable_cost_uzs=_money(variable_cost_month),
                fixed_cost_uzs=_money(fixed_cost_month),
                loan_payment_uzs=_money(loan_payment),
                tax_uzs=_money(tax_month),
                net_cashflow_uzs=_signed_money(net_cashflow_month),
                cumulative_cash_p10_uzs=_signed_money(
                    np.quantile(cash_paths[:, month_idx], 0.10)
                ),
                cumulative_cash_p50_uzs=_signed_money(
                    np.quantile(cash_paths[:, month_idx], 0.50)
                ),
                cumulative_cash_p90_uzs=_signed_money(
                    np.quantile(cash_paths[:, month_idx], 0.90)
                ),
                probability_negative_cash=round(
                    float(np.mean(cash_paths[:, month_idx] < 0)),
                    4,
                ),
                is_break_even_month=month_number == break_even_month,
            )
        )

    p10_final = float(np.quantile(final_cash, 0.10))
    median_final = float(np.quantile(final_cash, 0.50))
    p90_final = float(np.quantile(final_cash, 0.90))
    worst_month_cash = float(np.quantile(min_cash_with_initial, 0.10))
    min_required_capital = max(0.0, -worst_month_cash)

    margin_score = max(0.0, min(1.0, (data.gross_margin_pct - 0.15) / 0.45))
    runway_score = min(1.0, runway_months / min(24, months))
    break_even_score = probability_break_even
    score = (
        survival_probability * 0.45
        + runway_score * 0.25
        + break_even_score * 0.20
        + margin_score * 0.10
    ) * 100
    score = round(max(0.0, min(100.0, score)), 1)
    confidence_score = min(
        0.95,
        0.55
        + min(iterations, 5000) / 20000
        + max(0.0, min(0.15, 0.30 - volatility)) / 2,
    )

    return ViabilityModelResult(
        break_even_month=break_even_month,
        runway_months=round(runway_months, 1),
        survival_probability_24m=round(survival_probability, 4),
        cash_out_probability_24m=round(cash_out_probability, 4),
        probability_break_even_24m=round(probability_break_even, 4),
        median_final_cash_uzs=_signed_money(median_final),
        p10_final_cash_uzs=_signed_money(p10_final),
        p90_final_cash_uzs=_signed_money(p90_final),
        worst_month_cash_uzs=_signed_money(worst_month_cash),
        min_required_capital_uzs=_money(min_required_capital),
        viability_score=score,
        recommendation=_recommendation(
            score, survival_probability, probability_break_even
        ),
        confidence_score=round(confidence_score, 3),
        methodology_notes={
            "method": "financial_model_monte_carlo",
            "revenue_distribution": "lognormal",
            "iterations": iterations,
            "simulation_months": months,
            "monthly_inflation_pct": round(monthly_inflation, 5),
            "monthly_macro_growth_pct": round(monthly_macro, 5),
            "competitor_pressure_pct": round(competitor_pressure, 4),
            "failure_prior_pct": round(failure_prior, 4),
            "z_score_90": round(normal.inv_cdf(0.90), 4),
        },
        months=monthly_results,
    )
