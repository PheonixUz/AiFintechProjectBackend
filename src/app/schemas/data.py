from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel

# ── MCC Kategoriyalar ──────────────────────────────────────────────────────────


class MCCCategoryOut(BaseModel):
    mcc_code: str
    category_name_en: str
    niche_name_uz: str
    niche_name_ru: str
    parent_category: str
    is_active: bool

    model_config = {"from_attributes": True}


# ── Benchmarklar ───────────────────────────────────────────────────────────────


class BenchmarkOut(BaseModel):
    mcc_code: str
    niche: str
    city: str
    avg_monthly_revenue_uzs: Decimal
    median_monthly_revenue_uzs: Decimal
    p25_monthly_revenue_uzs: Decimal
    p75_monthly_revenue_uzs: Decimal
    avg_monthly_transactions: int
    avg_check_uzs: Decimal
    gross_margin_pct: float
    avg_employee_count: float
    revenue_per_sqm_monthly_uzs: Decimal | None
    annual_growth_rate_pct: float
    data_year: int
    data_source: str

    model_config = {"from_attributes": True}


# ── Raqobatchilar ──────────────────────────────────────────────────────────────


class CompetitorOut(BaseModel):
    id: int
    name: str | None
    niche: str
    lat: float
    lon: float
    distance_m: float = 0.0
    district: str | None
    city: str
    is_active: bool
    registered_date: date
    employee_count_est: int | None
    monthly_revenue_est_uzs: Decimal | None

    model_config = {"from_attributes": True}


class CompetitorListOut(BaseModel):
    mcc_code: str
    lat: float
    lon: float
    radius_m: float
    total_count: int
    competitors: list[CompetitorOut]


# ── Tranzaksiya statistikasi ───────────────────────────────────────────────────


class TransactionMonthOut(BaseModel):
    month: int
    total_uzs: Decimal
    transaction_count: int


class TransactionSummaryOut(BaseModel):
    mcc_code: str
    city: str
    year: int
    annual_total_uzs: Decimal
    monthly_breakdown: list[TransactionMonthOut]
    months_with_data: int


# ── Aholi zonalari ─────────────────────────────────────────────────────────────


class PopulationZoneOut(BaseModel):
    id: int
    zone_name: str
    district: str
    city: str
    lat: float
    lon: float
    radius_m: float
    total_population: int
    working_age_population: int
    youth_population: int
    avg_monthly_income_uzs: Decimal
    avg_monthly_spending_uzs: Decimal
    data_year: int

    model_config = {"from_attributes": True}


class PopulationListOut(BaseModel):
    lat: float
    lon: float
    radius_m: float
    zones_count: int
    total_population: int
    zones: list[PopulationZoneOut]


# ── POI (Qiziqish nuqtalari) ───────────────────────────────────────────────────


class POIOut(BaseModel):
    id: int
    name: str
    poi_type: str
    lat: float
    lon: float
    distance_m: float = 0.0
    district: str | None
    city: str
    capacity_est: int | None
    daily_visitors_est: int | None
    is_active: bool

    model_config = {"from_attributes": True}


class POIListOut(BaseModel):
    lat: float
    lon: float
    radius_m: float
    poi_type: str | None
    total_count: int
    pois: list[POIOut]


# ── Mijoz segmentlari ──────────────────────────────────────────────────────────


class CustomerSegmentOut(BaseModel):
    id: int
    segment_name: str
    district: str
    city: str
    lat: float
    lon: float
    radius_m: float
    avg_monthly_spending_uzs: Decimal
    purchase_frequency_monthly: float
    avg_check_uzs: Decimal
    top_mcc_categories: list
    spending_distribution: dict
    estimated_count: int
    data_year: int

    model_config = {"from_attributes": True}


class CustomerSegmentListOut(BaseModel):
    lat: float
    lon: float
    radius_m: float
    segments_count: int
    total_customers_est: int
    segments: list[CustomerSegmentOut]


# ── Saqlangan bozor tahminlari ─────────────────────────────────────────────────


class MarketEstimateOut(BaseModel):
    id: int
    niche: str
    mcc_code: str
    city: str
    lat: float
    lon: float
    radius_m: float
    tam_uzs: Decimal
    sam_uzs: Decimal
    som_uzs: Decimal
    competitor_count: int
    market_growth_rate_pct: float
    confidence_score: float
    calculation_date: date
    created_at: datetime

    model_config = {"from_attributes": True}
