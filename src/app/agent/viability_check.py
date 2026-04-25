"""M-D1 Financial Viability Check agenti."""

import logging
from decimal import Decimal

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from sqlalchemy.ext.asyncio import AsyncSession

from app.algorithms.viability_check import (
    ViabilityModelInput,
    ViabilityModelResult,
    run_viability_check,
)
from app.config import settings
from app.db.models.financial import SectorFinancialBenchmark
from app.db.repositories.financial_repo import (
    DEFAULT_FINANCIAL_BENCHMARK,
    FinancialRepository,
)
from app.schemas.request import ViabilityCheckRequest
from app.schemas.response import (
    ViabilityCashflowMonthOut,
    ViabilityCheckResponse,
)

logger = logging.getLogger(__name__)


def _format_money(value: Decimal) -> str:
    return f"{float(value) / 1_000_000:.1f} mln UZS"


def _benchmark_value(
    benchmark: SectorFinancialBenchmark | None,
    field: str,
) -> Decimal | float:
    if benchmark is None:
        return DEFAULT_FINANCIAL_BENCHMARK[field]
    return getattr(benchmark, field)


def _seasonality(profile: dict[str, float] | None) -> dict[int, float]:
    if not profile:
        return {
            1: 0.94,
            2: 0.96,
            3: 1.00,
            4: 1.02,
            5: 1.03,
            6: 1.01,
            7: 0.98,
            8: 0.99,
            9: 1.02,
            10: 1.05,
            11: 1.08,
            12: 1.12,
        }
    return {int(month): float(value) for month, value in profile.items()}


def _fallback_summary(
    req: ViabilityCheckRequest,
    result: ViabilityModelResult,
    niche: str,
) -> str:
    break_even_text = (
        f"{result.break_even_month}-oyda break-even ehtimoli bor"
        if result.break_even_month
        else "24 oy ichida aniq break-even ko'rinmayapti"
    )
    return (
        f"{niche} biznes-rejasi uchun viability score "
        f"{result.viability_score:.1f}/100. "
        f"{break_even_text}; runway median {result.runway_months:.1f} oy. "
        f"24 oylik yashab ketish ehtimoli {result.survival_probability_24m:.0%}, "
        f"yakuniy median cash {_format_money(result.median_final_cash_uzs)}. "
        f"Tavsiya: {result.recommendation}."
    )


def _build_synthesis_prompt(
    req: ViabilityCheckRequest,
    result: ViabilityModelResult,
    niche: str,
) -> str:
    return (
        f"{req.city} shahrida {niche} uchun M-D1 Financial Viability Check "
        "hisoblandi.\n\n"
        f"Initial capital: {_format_money(req.initial_capital_uzs)}\n"
        f"Break-even month: {result.break_even_month}\n"
        f"Runway: {result.runway_months:.1f} oy\n"
        f"Survival probability 24m: {result.survival_probability_24m:.0%}\n"
        f"Cash-out probability 24m: {result.cash_out_probability_24m:.0%}\n"
        f"Median final cash: {_format_money(result.median_final_cash_uzs)}\n"
        f"P10 final cash: {_format_money(result.p10_final_cash_uzs)}\n"
        f"Min required capital: {_format_money(result.min_required_capital_uzs)}\n"
        f"Recommendation: {result.recommendation}\n\n"
        "O'zbek tilida 4-6 gaplik professional bank analitik xulosa yoz: "
        "break-even, runway, asosiy risklar, kapital yetarliligi va qaror."
    )


class ViabilityCheckAgent:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = FinancialRepository(session)

    async def run(self, req: ViabilityCheckRequest) -> ViabilityCheckResponse:
        category = await self._repo.get_mcc_category(req.mcc_code)
        benchmark = await self._repo.get_latest_benchmark(
            mcc_code=req.mcc_code,
            city=req.city,
        )
        if category is None and req.niche is None:
            raise RuntimeError("MCC kodi uchun niche topilmadi")

        niche = req.niche or category.niche_name_uz  # type: ignore[union-attr]
        gross_margin = float(
            req.gross_margin_pct
            if req.gross_margin_pct is not None
            else _benchmark_value(benchmark, "gross_margin_pct")
        )
        variable_cost = float(
            req.variable_cost_pct
            if req.variable_cost_pct is not None
            else _benchmark_value(benchmark, "variable_cost_pct")
        )
        expected_revenue = req.expected_monthly_revenue_uzs or Decimal(
            _benchmark_value(benchmark, "avg_monthly_revenue_uzs")
        )
        startup_capex = req.startup_capex_uzs or Decimal(
            _benchmark_value(benchmark, "startup_capex_median_uzs")
        )
        default_fixed_cost = expected_revenue * Decimal(
            str(_benchmark_value(benchmark, "fixed_cost_ratio_pct"))
        )
        fixed_parts_total = (
            req.monthly_rent_uzs
            + req.monthly_payroll_uzs
            + req.monthly_utilities_uzs
            + req.monthly_marketing_uzs
            + req.monthly_other_fixed_uzs
        )
        monthly_fixed_cost = (
            req.monthly_fixed_cost_uzs or fixed_parts_total or default_fixed_cost
        )
        working_capital = max(Decimal("0"), req.initial_capital_uzs - startup_capex)

        competitor_count = await self._repo.get_active_competitor_count(
            mcc_code=req.mcc_code,
            city=req.city,
            lat=req.lat,
            lon=req.lon,
            radius_m=req.radius_m,
        )

        algo_input = ViabilityModelInput(
            initial_capital_uzs=req.initial_capital_uzs,
            startup_capex_uzs=startup_capex,
            expected_monthly_revenue_uzs=expected_revenue,
            gross_margin_pct=gross_margin,
            variable_cost_pct=variable_cost,
            monthly_fixed_cost_uzs=monthly_fixed_cost,
            monthly_loan_payment_uzs=req.monthly_loan_payment_uzs,
            owner_draw_uzs=req.owner_draw_uzs,
            monthly_revenue_growth_pct=float(
                req.monthly_revenue_growth_pct
                if req.monthly_revenue_growth_pct is not None
                else _benchmark_value(benchmark, "monthly_growth_pct")
            ),
            revenue_volatility_pct=float(
                req.revenue_volatility_pct
                if req.revenue_volatility_pct is not None
                else _benchmark_value(benchmark, "revenue_volatility_pct")
            ),
            annual_inflation_rate_pct=req.annual_inflation_rate_pct,
            annual_macro_growth_pct=req.annual_macro_growth_pct,
            tax_rate_pct=req.tax_rate_pct,
            simulation_months=req.simulation_months,
            monte_carlo_iterations=req.monte_carlo_iterations,
            seasonality_profile=_seasonality(req.seasonality_profile),
            competitor_count_radius=competitor_count,
            two_year_failure_rate_pct=float(
                _benchmark_value(benchmark, "two_year_failure_rate_pct")
            ),
            clean_anomalies=req.clean_anomalies,
            random_seed=req.random_seed,
        )
        algo_result = run_viability_check(algo_input)

        analysis_text = _fallback_summary(req, algo_result, niche)
        if settings.google_api_key:
            llm = ChatGoogleGenerativeAI(
                model=settings.google_model,
                google_api_key=settings.google_api_key,
            )
            synthesis = await llm.ainvoke(
                [
                    SystemMessage(
                        content=(
                            "Sen bank uchun M-D1 Financial Viability Check "
                            "agentisan. Xulosani o'zbek tilida, aniq va "
                            "risklarni yashirmasdan yoz."
                        )
                    ),
                    HumanMessage(
                        content=_build_synthesis_prompt(req, algo_result, niche)
                    ),
                ]
            )
            if isinstance(synthesis.content, str) and synthesis.content.strip():
                analysis_text = synthesis.content

        monthly_other_fixed = req.monthly_other_fixed_uzs
        if fixed_parts_total == 0:
            monthly_other_fixed = monthly_fixed_cost

        saved_run = await self._repo.save_viability_result(
            assumption_payload={
                "plan_name": req.plan_name,
                "mcc_code": req.mcc_code,
                "niche": niche,
                "city": req.city,
                "lat": req.lat,
                "lon": req.lon,
                "radius_m": req.radius_m,
                "initial_capital_uzs": req.initial_capital_uzs,
                "startup_capex_uzs": startup_capex,
                "working_capital_uzs": working_capital,
                "loan_amount_uzs": req.loan_amount_uzs,
                "monthly_loan_payment_uzs": req.monthly_loan_payment_uzs,
                "expected_monthly_revenue_uzs": expected_revenue,
                "avg_ticket_uzs": req.avg_ticket_uzs,
                "expected_monthly_transactions": req.expected_monthly_transactions,
                "gross_margin_pct": gross_margin,
                "variable_cost_pct": variable_cost,
                "monthly_fixed_cost_uzs": monthly_fixed_cost,
                "monthly_rent_uzs": req.monthly_rent_uzs,
                "monthly_payroll_uzs": req.monthly_payroll_uzs,
                "monthly_utilities_uzs": req.monthly_utilities_uzs,
                "monthly_marketing_uzs": req.monthly_marketing_uzs,
                "monthly_other_fixed_uzs": monthly_other_fixed,
                "monthly_revenue_growth_pct": algo_input.monthly_revenue_growth_pct,
                "revenue_volatility_pct": algo_input.revenue_volatility_pct,
                "tax_rate_pct": req.tax_rate_pct,
                "owner_draw_uzs": req.owner_draw_uzs,
                "seasonality_profile": {
                    str(key): value
                    for key, value in algo_input.seasonality_profile.items()
                },
                "risk_assumptions": {
                    **(req.risk_assumptions or {}),
                    "competitor_count_radius": competitor_count,
                    "benchmark_source": "db" if benchmark else "default",
                },
                "created_by": "viability_check_agent",
            },
            run_payload={
                "mcc_code": req.mcc_code,
                "niche": niche,
                "city": req.city,
                "simulation_months": req.simulation_months,
                "monte_carlo_iterations": req.monte_carlo_iterations,
                "random_seed": req.random_seed,
                "break_even_month": algo_result.break_even_month,
                "runway_months": algo_result.runway_months,
                "survival_probability_24m": algo_result.survival_probability_24m,
                "cash_out_probability_24m": algo_result.cash_out_probability_24m,
                "probability_break_even_24m": algo_result.probability_break_even_24m,
                "median_final_cash_uzs": algo_result.median_final_cash_uzs,
                "p10_final_cash_uzs": algo_result.p10_final_cash_uzs,
                "p90_final_cash_uzs": algo_result.p90_final_cash_uzs,
                "worst_month_cash_uzs": algo_result.worst_month_cash_uzs,
                "min_required_capital_uzs": algo_result.min_required_capital_uzs,
                "viability_score": algo_result.viability_score,
                "recommendation": algo_result.recommendation,
                "confidence_score": algo_result.confidence_score,
                "analysis_summary": analysis_text,
                "calc_metadata": algo_result.methodology_notes,
            },
            cashflow_payloads=[
                {
                    "month_index": month.month_index,
                    "expected_revenue_uzs": month.expected_revenue_uzs,
                    "p10_revenue_uzs": month.p10_revenue_uzs,
                    "p90_revenue_uzs": month.p90_revenue_uzs,
                    "variable_cost_uzs": month.variable_cost_uzs,
                    "fixed_cost_uzs": month.fixed_cost_uzs,
                    "loan_payment_uzs": month.loan_payment_uzs,
                    "tax_uzs": month.tax_uzs,
                    "net_cashflow_uzs": month.net_cashflow_uzs,
                    "cumulative_cash_p10_uzs": month.cumulative_cash_p10_uzs,
                    "cumulative_cash_p50_uzs": month.cumulative_cash_p50_uzs,
                    "cumulative_cash_p90_uzs": month.cumulative_cash_p90_uzs,
                    "probability_negative_cash": month.probability_negative_cash,
                    "is_break_even_month": month.is_break_even_month,
                }
                for month in algo_result.months
            ],
        )

        ordered_months = sorted(
            saved_run.cashflow_months,
            key=lambda month: month.month_index,
        )
        return ViabilityCheckResponse(
            run_id=saved_run.id,
            assumption_id=saved_run.assumption_id,
            niche=niche,
            mcc_code=req.mcc_code,
            city=req.city,
            simulation_months=saved_run.simulation_months,
            monte_carlo_iterations=saved_run.monte_carlo_iterations,
            break_even_month=saved_run.break_even_month,
            runway_months=saved_run.runway_months,
            survival_probability_24m=saved_run.survival_probability_24m,
            cash_out_probability_24m=saved_run.cash_out_probability_24m,
            probability_break_even_24m=saved_run.probability_break_even_24m,
            median_final_cash_uzs=saved_run.median_final_cash_uzs,
            p10_final_cash_uzs=saved_run.p10_final_cash_uzs,
            p90_final_cash_uzs=saved_run.p90_final_cash_uzs,
            worst_month_cash_uzs=saved_run.worst_month_cash_uzs,
            min_required_capital_uzs=saved_run.min_required_capital_uzs,
            viability_score=saved_run.viability_score,
            recommendation=saved_run.recommendation,
            confidence_score=saved_run.confidence_score,
            analysis_summary=analysis_text,
            methodology_notes=saved_run.calc_metadata,
            cashflow_months=[
                ViabilityCashflowMonthOut.model_validate(month)
                for month in ordered_months
            ],
        )
