"""Test uchun sintetik ob'ektlar yaratuvchi factory funksiyalar."""

from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock


# ── Mock session ───────────────────────────────────────────────────────────────

def make_async_session(scalars_result=None, scalar_result=None, rows_result=None):
    """Mock AsyncSession qaytaradi."""
    session = AsyncMock()
    execute_result = MagicMock()

    scalars_mock = MagicMock()
    scalars_mock.all.return_value = scalars_result or []
    execute_result.scalars.return_value = scalars_mock
    execute_result.scalar_one_or_none.return_value = scalar_result
    execute_result.all.return_value = rows_result or []

    session.execute.return_value = execute_result
    return session


# ── DB ob'ektlari ──────────────────────────────────────────────────────────────

def make_mcc_category(**kwargs):
    defaults = dict(
        id=1, mcc_code="5812",
        category_name_en="Eating Places, Restaurants",
        niche_name_uz="Restoran", niche_name_ru="Ресторан",
        parent_category="Oziq-ovqat", is_active=True,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def make_benchmark(**kwargs):
    defaults = dict(
        id=1, mcc_code="5812", niche="restoran", city="Toshkent",
        avg_monthly_revenue_uzs=Decimal("50_000_000"),
        median_monthly_revenue_uzs=Decimal("40_000_000"),
        p25_monthly_revenue_uzs=Decimal("25_000_000"),
        p75_monthly_revenue_uzs=Decimal("75_000_000"),
        avg_monthly_transactions=300,
        avg_check_uzs=Decimal("85_000"),
        gross_margin_pct=0.30,
        avg_employee_count=5.5,
        revenue_per_sqm_monthly_uzs=Decimal("500_000"),
        annual_growth_rate_pct=0.08,
        data_year=2025,
        data_source="bank_transactions",
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def make_business(**kwargs):
    defaults = dict(
        id=1, name="Test Restoran", niche="restoran",
        mcc_code="5812",
        lat=41.3, lon=69.3,
        district="Yunusobod", city="Toshkent",
        address="Amir Temur ko'chasi 1",
        is_active=True,
        registered_date=date(2022, 1, 1),
        closed_date=None,
        employee_count_est=5,
        monthly_revenue_est_uzs=Decimal("50_000_000"),
        area_sqm=50.0,
        source="bank_registry",
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def make_population_zone(**kwargs):
    defaults = dict(
        id=1, zone_name="Yunusobod 1", district="Yunusobod",
        city="Toshkent", lat=41.3, lon=69.3, radius_m=500.0,
        total_population=15_000,
        working_age_population=9_000,
        youth_population=4_000,
        avg_monthly_income_uzs=Decimal("3_500_000"),
        avg_monthly_spending_uzs=Decimal("2_450_000"),
        data_year=2025,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def make_poi(**kwargs):
    defaults = dict(
        id=1, name="Chorsu bozori", poi_type="market",
        lat=41.3, lon=69.3,
        district="Eski shahar", city="Toshkent",
        capacity_est=1000, daily_visitors_est=5000,
        is_active=True,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def make_customer_segment(**kwargs):
    defaults = dict(
        id=1, segment_name="mass_market",
        district="Yunusobod", city="Toshkent",
        lat=41.3, lon=69.3, radius_m=500.0,
        avg_monthly_spending_uzs=Decimal("1_500_000"),
        purchase_frequency_monthly=8.5,
        avg_check_uzs=Decimal("180_000"),
        top_mcc_categories=["5812", "5411"],
        spending_distribution={"5812": 0.35, "5411": 0.25},
        estimated_count=5000,
        data_year=2025,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def make_market_estimate(**kwargs):
    defaults = dict(
        id=1, niche="restoran", mcc_code="5812", city="Toshkent",
        lat=41.3, lon=69.3, radius_m=1000.0,
        tam_uzs=Decimal("12_000_000_000"),
        sam_uzs=Decimal("1_200_000_000"),
        som_uzs=Decimal("240_000_000"),
        competitor_count=4,
        market_growth_rate_pct=0.08,
        confidence_score=0.75,
        calculation_date=date(2025, 4, 25),
        created_at=datetime(2025, 4, 25, 10, 0, 0),
        calc_metadata={},
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)
