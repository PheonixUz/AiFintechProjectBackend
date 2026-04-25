"""
Fake data seed script — AI agent test qilish uchun.

Usage:
    uv run python scripts/seed_db.py
    uv run python scripts/seed_db.py --clear   # Avval tozalab, keyin to'ldiradi
"""

import argparse
import asyncio
import random
import sys
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.db.models.business import Business
from app.db.models.churn import (
    ChurnFeatureSnapshot,
    ChurnModelVersion,
    ChurnPredictionRun,
    ChurnRiskFactor,
)
from app.db.models.customer import CustomerSegment
from app.db.models.financial import (
    SectorFinancialBenchmark,
    ViabilityCashflowMonth,
    ViabilityCheckRun,
    ViabilityPlanAssumption,
)
from app.db.models.forecast import (
    DemandForecastPoint,
    DemandForecastRun,
    NicheMonthlyRevenue,
)
from app.db.models.location import PointOfInterest, PopulationZone
from app.db.models.market import MarketBenchmark, MarketSizeEstimate
from app.db.models.transaction import MCCCategory, Transaction

# ─── Sozlamalar ──────────────────────────────────────────────────────────────

CITY = "Toshkent"
SEED = 42
random.seed(SEED)

# Toshkent markaziy koordinatalari
TASHKENT_CENTER = (41.2995, 69.2401)

# Toshkent tumanlari (nomi, markaz lat, lon)
DISTRICTS = [
    ("Yunusobod", 41.3368, 69.2861),
    ("Chilonzor", 41.2756, 69.1989),
    ("Mirzo Ulug'bek", 41.3207, 69.3017),
    ("Shayxontohur", 41.3089, 69.2244),
    ("Yakkasaroy", 41.2889, 69.2608),
    ("Hamza", 41.2697, 69.2303),
    ("Sergeli", 41.2214, 69.2464),
    ("Uchtepa", 41.2950, 69.1803),
    ("Bektemir", 41.2231, 69.3250),
    ("Olmazor", 41.3456, 69.2150),
    ("Yashnobod", 41.2503, 69.3050),
    ("Zangiota", 41.2100, 69.1800),
]

# ─── MCC Kategoriyalar ────────────────────────────────────────────────────────

MCC_DATA = [
    # (mcc_code, category_name_en, niche_name_uz, niche_name_ru, parent_category)
    (
        "5411",
        "Grocery Stores",
        "Oziq-ovqat do'koni",
        "Продуктовый магазин",
        "Oziq-ovqat",
    ),
    ("5812", "Eating Places, Restaurants", "Restoran", "Ресторан", "Oziq-ovqat"),
    ("5814", "Fast Food Restaurants", "Tez ovqat", "Фаст-фуд", "Oziq-ovqat"),
    ("5912", "Drug Stores and Pharmacies", "Dorixona", "Аптека", "Sog'liqni saqlash"),
    ("7011", "Hotels and Motels", "Mehmonxona", "Гостиница", "Xizmatlar"),
    (
        "5621",
        "Women's Ready-To-Wear Stores",
        "Ayollar kiyimi",
        "Женская одежда",
        "Kiyim-kechak",
    ),
    (
        "5611",
        "Men's Clothing Stores",
        "Erkaklar kiyimi",
        "Мужская одежда",
        "Kiyim-kechak",
    ),
    (
        "5945",
        "Hobby, Toy, and Game Shops",
        "O'yinchoq do'koni",
        "Игрушки",
        "Ko'ngilochar",
    ),
    ("7230", "Beauty Shops", "Go'zallik saloni", "Салон красоты", "Xizmatlar"),
    ("7011", "Fitness Centers", "Sport zali", "Фитнес-зал", "Sport"),
    ("5251", "Hardware Stores", "Qurilish mollari", "Стройматериалы", "Qurilish"),
    ("5065", "Electronic Parts", "Elektronika do'koni", "Электроника", "Texnika"),
    ("7542", "Car Washes", "Avtomobil yuvish", "Автомойка", "Avtomobil xizmatlari"),
    ("5441", "Candy Stores", "Shirinliklar do'koni", "Кондитерская", "Oziq-ovqat"),
    ("5999", "Other Retail", "Boshqa savdo", "Прочая торговля", "Savdo"),
]


# ─── Yordamchi funksiyalar ────────────────────────────────────────────────────


def rand_coord_near(
    lat: float, lon: float, radius_km: float = 2.0
) -> tuple[float, float]:
    dlat = random.uniform(-radius_km / 111, radius_km / 111)
    dlon = random.uniform(-radius_km / 85, radius_km / 85)
    return round(lat + dlat, 6), round(lon + dlon, 6)


def rand_date(start: date, end: date) -> date:
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta))


def add_months(month: date, count: int) -> date:
    total_month = month.month - 1 + count
    year = month.year + total_month // 12
    return date(year, total_month % 12 + 1, 1)


def uzs(amount: int, variation: float = 0.3) -> Decimal:
    factor = 1 + random.uniform(-variation, variation)
    return Decimal(str(round(amount * factor, 2)))


# ─── Seed funksiyalari ────────────────────────────────────────────────────────


async def seed_mcc_categories(session: AsyncSession) -> list[MCCCategory]:
    print("  MCCCategory yozilmoqda...")
    # Duplikat mcc_code larni filterlash (masalan, 7011 ikki marta bor)
    seen = set()
    categories = []
    for row in MCC_DATA:
        mcc_code = row[0]
        if mcc_code in seen:
            # Kodni biroz o'zgartirish
            mcc_code = str(int(mcc_code) + len(seen))
        seen.add(mcc_code)
        cat = MCCCategory(
            mcc_code=mcc_code,
            category_name_en=row[1],
            niche_name_uz=row[2],
            niche_name_ru=row[3],
            parent_category=row[4],
            is_active=True,
        )
        session.add(cat)
        categories.append(cat)
    await session.flush()
    print(f"    {len(categories)} ta kategoriya qo'shildi")
    return categories


async def seed_transactions(
    session: AsyncSession, mcc_codes: list[str], count: int = 5000
) -> None:
    print(f"  Transaction yozilmoqda ({count} ta)...")
    age_groups = ["18-25", "26-35", "36-50", "50+"]
    genders = ["M", "F"]
    end_date = date(2026, 4, 25)
    start_date = date(2024, 1, 1)

    transactions = []
    for _ in range(count):
        district_name, dlat, dlon = random.choice(DISTRICTS)
        lat, lon = rand_coord_near(dlat, dlon, 1.5)
        mcc_code = random.choice(mcc_codes)

        # Turli MCC uchun turli summalar
        if mcc_code in ("5411", "5814"):
            amount = random.randint(15_000, 150_000)
        elif mcc_code in ("5812",):
            amount = random.randint(30_000, 300_000)
        elif mcc_code in ("5912",):
            amount = random.randint(10_000, 80_000)
        elif mcc_code in ("5621", "5611"):
            amount = random.randint(100_000, 1_500_000)
        else:
            amount = random.randint(20_000, 500_000)

        t = Transaction(
            transaction_date=rand_date(start_date, end_date),
            amount_uzs=Decimal(amount),
            mcc_code=mcc_code,
            merchant_lat=lat,
            merchant_lon=lon,
            merchant_district=district_name,
            merchant_city=CITY,
            customer_age_group=random.choice(age_groups),
            customer_gender=random.choice(genders),
            is_online=random.random() < 0.15,
        )
        transactions.append(t)

    session.add_all(transactions)
    await session.flush()
    print(f"    {count} ta tranzaksiya qo'shildi")


async def seed_businesses(session: AsyncSession, mcc_data: list[tuple]) -> None:
    print("  Business yozilmoqda...")
    businesses = []
    today = date(2026, 4, 25)

    for district_name, dlat, dlon in DISTRICTS:
        for mcc_code, _, niche_uz, _, _ in mcc_data[:10]:  # har tumanda 10 nisha
            count = random.randint(2, 8)
            for i in range(count):
                lat, lon = rand_coord_near(dlat, dlon, 2.0)
                opened = rand_date(date(2018, 1, 1), date(2025, 12, 1))

                earliest_close = opened + timedelta(days=180)
                can_be_closed = earliest_close < today
                is_active = not can_be_closed or random.random() > 0.25
                closed_date = None
                if not is_active:
                    closed_date = rand_date(earliest_close, today)

                b = Business(
                    name=f"{niche_uz} #{i + 1} ({district_name})",
                    mcc_code=mcc_code,
                    niche=niche_uz,
                    lat=lat,
                    lon=lon,
                    district=district_name,
                    city=CITY,
                    address=f"{district_name} ko'chasi, {random.randint(1, 200)}-uy",
                    registered_date=opened,
                    closed_date=closed_date,
                    is_active=is_active,
                    last_observed_active_date=closed_date or today,
                    closure_reason=(
                        random.choice(
                            [
                                "revenue_drop",
                                "low_transaction_activity",
                                "high_competition",
                                "owner_exit",
                            ]
                        )
                        if closed_date
                        else None
                    ),
                    closure_confidence_score=(
                        round(random.uniform(0.72, 0.96), 2) if closed_date else None
                    ),
                    employee_count_est=random.randint(1, 25),
                    monthly_revenue_est_uzs=uzs(random.randint(3_000_000, 50_000_000)),
                    area_sqm=round(random.uniform(20, 300), 1),
                    source="bank_registry",
                )
                businesses.append(b)

    session.add_all(businesses)
    await session.flush()
    print(f"    {len(businesses)} ta biznes qo'shildi")


async def seed_market_benchmarks(session: AsyncSession, mcc_data: list[tuple]) -> None:
    print("  MarketBenchmark yozilmoqda...")
    benchmarks = []
    for mcc_code, _, niche_uz, _, parent in mcc_data:
        # Nisha turiga qarab bazaviy daromad
        base_revenue = {
            "Oziq-ovqat": 15_000_000,
            "Sog'liqni saqlash": 12_000_000,
            "Kiyim-kechak": 20_000_000,
            "Xizmatlar": 8_000_000,
            "Sport": 10_000_000,
            "Qurilish": 18_000_000,
            "Texnika": 25_000_000,
            "Ko'ngilochar": 6_000_000,
            "Avtomobil xizmatlari": 9_000_000,
            "Savdo": 14_000_000,
        }.get(parent, 12_000_000)

        avg_rev = int(base_revenue * random.uniform(0.85, 1.15))
        bm = MarketBenchmark(
            mcc_code=mcc_code,
            niche=niche_uz,
            city=CITY,
            avg_monthly_revenue_uzs=Decimal(avg_rev),
            median_monthly_revenue_uzs=Decimal(int(avg_rev * 0.9)),
            p25_monthly_revenue_uzs=Decimal(int(avg_rev * 0.6)),
            p75_monthly_revenue_uzs=Decimal(int(avg_rev * 1.4)),
            avg_monthly_transactions=random.randint(100, 800),
            avg_check_uzs=Decimal(random.randint(20_000, 200_000)),
            gross_margin_pct=round(random.uniform(0.20, 0.55), 2),
            avg_employee_count=round(random.uniform(2.0, 12.0), 1),
            revenue_per_sqm_monthly_uzs=Decimal(random.randint(200_000, 800_000)),
            annual_growth_rate_pct=round(random.uniform(-0.05, 0.20), 3),
            data_year=2026,
            data_source="bank_transactions",
        )
        benchmarks.append(bm)

    session.add_all(benchmarks)
    await session.flush()
    print(f"    {len(benchmarks)} ta benchmark qo'shildi")


async def seed_population_zones(session: AsyncSession) -> None:
    print("  PopulationZone yozilmoqda...")
    zones = []
    for district_name, dlat, dlon in DISTRICTS:
        zone_count = random.randint(3, 6)
        for j in range(zone_count):
            lat, lon = rand_coord_near(dlat, dlon, 2.0)
            pop = random.randint(8_000, 45_000)
            avg_income = random.randint(2_500_000, 8_000_000)
            z = PopulationZone(
                zone_name=f"{district_name} zona-{j + 1}",
                district=district_name,
                city=CITY,
                lat=lat,
                lon=lon,
                radius_m=random.choice([500, 700, 1000]),
                total_population=pop,
                working_age_population=int(pop * random.uniform(0.55, 0.65)),
                youth_population=int(pop * random.uniform(0.25, 0.35)),
                avg_monthly_income_uzs=Decimal(avg_income),
                avg_monthly_spending_uzs=Decimal(
                    int(avg_income * random.uniform(0.60, 0.75))
                ),
                data_year=2026,
            )
            zones.append(z)

    session.add_all(zones)
    await session.flush()
    print(f"    {len(zones)} ta aholi zonasi qo'shildi")


async def seed_poi(session: AsyncSession) -> None:
    print("  PointOfInterest yozilmoqda...")
    poi_templates = [
        ("market", "Bozor", 5000, 8000),
        ("mosque", "Masjid", 2000, 3000),
        ("school", "Maktab", 1200, 1500),
        ("mall", "Savdo markazi", 10000, 15000),
        ("park", "Park", 3000, 5000),
        ("hospital", "Kasalxona", 500, 800),
        ("university", "Universitet", 8000, 12000),
        ("transport_hub", "Avtobus bekat", 2000, 4000),
        ("metro", "Metro bekat", 5000, 9000),
    ]
    pois = []
    for district_name, dlat, dlon in DISTRICTS:
        for poi_type, base_name, cap_min, cap_max in poi_templates:
            count = (
                random.randint(1, 4)
                if poi_type in ("mosque", "school", "transport_hub")
                else 1
            )
            for k in range(count):
                lat, lon = rand_coord_near(dlat, dlon, 2.5)
                capacity = random.randint(cap_min, cap_max)
                poi_suffix = f" #{k + 1}" if count > 1 else ""
                p = PointOfInterest(
                    name=f"{base_name} ({district_name}){poi_suffix}",
                    poi_type=poi_type,
                    lat=lat,
                    lon=lon,
                    district=district_name,
                    city=CITY,
                    capacity_est=capacity,
                    daily_visitors_est=int(capacity * random.uniform(0.3, 0.8)),
                    is_active=True,
                )
                pois.append(p)

    session.add_all(pois)
    await session.flush()
    print(f"    {len(pois)} ta POI qo'shildi")


async def seed_customer_segments(session: AsyncSession) -> None:
    print("  CustomerSegment yozilmoqda...")
    segment_profiles = [
        ("premium", 6_000_000, 12, 150_000),
        ("mass_market", 2_500_000, 20, 40_000),
        ("youth", 1_800_000, 25, 25_000),
        ("bargain_hunter", 1_200_000, 30, 18_000),
    ]
    top_mcc = ["5411", "5812", "5814", "5912", "5621"]
    segments = []

    for district_name, dlat, dlon in DISTRICTS:
        for seg_name, avg_spend, freq, avg_check in segment_profiles:
            lat, lon = rand_coord_near(dlat, dlon, 1.5)
            s = CustomerSegment(
                segment_name=seg_name,
                district=district_name,
                city=CITY,
                lat=lat,
                lon=lon,
                radius_m=random.choice([500, 700, 1000]),
                avg_monthly_spending_uzs=uzs(avg_spend, 0.2),
                purchase_frequency_monthly=round(freq * random.uniform(0.8, 1.2), 1),
                avg_check_uzs=uzs(avg_check, 0.25),
                top_mcc_categories=random.sample(top_mcc, 3),
                spending_distribution={
                    mcc: round(random.uniform(0.1, 0.4), 2)
                    for mcc in random.sample(top_mcc, 3)
                },
                estimated_count=random.randint(1_000, 15_000),
                data_year=2026,
            )
            segments.append(s)

    session.add_all(segments)
    await session.flush()
    print(f"    {len(segments)} ta segment qo'shildi")


async def seed_market_size_estimates(
    session: AsyncSession, mcc_data: list[tuple]
) -> None:
    print("  MarketSizeEstimate yozilmoqda...")
    estimates = []
    calc_date = date(2026, 4, 1)

    for district_name, dlat, dlon in DISTRICTS[:6]:  # 6 tumanда
        for mcc_code, _, niche_uz, _, _ in mcc_data[:8]:
            lat, lon = rand_coord_near(dlat, dlon, 0.5)
            tam = random.randint(50_000_000_000, 500_000_000_000)
            sam = int(tam * random.uniform(0.05, 0.20))
            som = int(sam * random.uniform(0.05, 0.15))
            e = MarketSizeEstimate(
                niche=niche_uz,
                mcc_code=mcc_code,
                city=CITY,
                lat=lat,
                lon=lon,
                radius_m=1000.0,
                tam_uzs=Decimal(tam),
                sam_uzs=Decimal(sam),
                som_uzs=Decimal(som),
                competitor_count=random.randint(3, 30),
                market_growth_rate_pct=round(random.uniform(-0.02, 0.18), 3),
                confidence_score=round(random.uniform(0.55, 0.90), 2),
                calc_metadata={
                    "method": "bottom_up",
                    "data_sources": ["bank_transactions", "population_zones"],
                    "transaction_count": random.randint(200, 2000),
                },
                calculation_date=calc_date,
            )
            estimates.append(e)

    session.add_all(estimates)
    await session.flush()
    print(f"    {len(estimates)} ta bozor bahosi qo'shildi")


# ─── Asosiy funksiya ──────────────────────────────────────────────────────────


async def seed_demand_forecasting(
    session: AsyncSession, categories: list[MCCCategory]
) -> None:
    print("  M-B1 Demand Forecasting ma'lumotlari yozilmoqda...")

    existing = await session.execute(select(DemandForecastRun).limit(1))
    if existing.scalar() is not None:
        print("    Forecast ma'lumotlari mavjud, o'tkazib yuborildi")
        return

    monthly_rows: list[NicheMonthlyRevenue] = []
    forecast_runs: list[DemandForecastRun] = []
    forecast_points: list[DemandForecastPoint] = []

    history_start = date(2023, 10, 1)
    history_months = 30
    forecast_start = date(2026, 4, 1)

    for idx, category in enumerate(categories[:10]):
        base_revenue = 350_000_000 + idx * 45_000_000
        monthly_growth = random.uniform(0.006, 0.025)
        seasonality_shift = random.randint(0, 11)
        latest_revenue = Decimal(0)

        for month_idx in range(history_months):
            month = add_months(history_start, month_idx)
            is_high_season = (month.month + seasonality_shift) % 12 in (3, 4, 10, 11)
            seasonal = 1.12 if is_high_season else 0.97
            trend = (1 + monthly_growth) ** month_idx
            revenue = Decimal(
                str(
                    round(
                        base_revenue * trend * seasonal * random.uniform(0.88, 1.12),
                        2,
                    )
                )
            )
            tx_count = random.randint(1200, 8500)
            latest_revenue = revenue
            monthly_rows.append(
                NicheMonthlyRevenue(
                    mcc_code=category.mcc_code,
                    niche=category.niche_name_uz,
                    city=CITY,
                    month=month,
                    revenue_uzs=revenue,
                    transaction_count=tx_count,
                    avg_check_uzs=Decimal(str(round(float(revenue) / tx_count, 2))),
                    active_business_count=random.randint(25, 180),
                    source="synthetic_bank_transactions",
                )
            )

        for horizon in (12, 24, 36):
            run = DemandForecastRun(
                niche=category.niche_name_uz,
                mcc_code=category.mcc_code,
                city=CITY,
                horizon_months=horizon,
                history_start_date=history_start,
                history_end_date=add_months(history_start, history_months - 1),
                forecast_start_month=forecast_start,
                model_name="lstm_prophet_ensemble",
                model_version="fake-v1",
                algorithm="LSTM + Facebook Prophet",
                confidence_level=0.95,
                training_sample_size=history_months,
                train_mape_pct=round(random.uniform(4.5, 13.5), 2),
                train_rmse_uzs=Decimal(str(random.randint(18_000_000, 95_000_000))),
                status="completed",
                analysis_summary=(
                    f"{category.niche_name_uz} nishasi uchun {horizon} oylik "
                    "fake forecast: trend, mavsumiylik va ishonch intervali."
                ),
                calc_metadata={
                    "source": "seed_db.py",
                    "model_components": ["lstm", "prophet"],
                    "seasonality": "monthly",
                    "is_fake_data": True,
                },
            )
            session.add(run)
            await session.flush()
            forecast_runs.append(run)

            for h in range(1, horizon + 1):
                forecast_month = add_months(forecast_start, h - 1)
                is_high_season = (forecast_month.month + seasonality_shift) % 12 in (
                    3,
                    4,
                    10,
                    11,
                )
                seasonal_factor = Decimal("1.10") if is_high_season else Decimal("0.97")
                growth_factor = Decimal(str((1 + monthly_growth) ** h))
                trend_component = latest_revenue * growth_factor
                prediction = trend_component * seasonal_factor
                widening = Decimal("0.12") + Decimal(str(h)) * Decimal("0.008")
                lower = prediction * (Decimal("1") - widening)
                upper = prediction * (Decimal("1") + widening)

                forecast_points.append(
                    DemandForecastPoint(
                        forecast_run_id=run.id,
                        forecast_month=forecast_month,
                        horizon_index=h,
                        predicted_revenue_uzs=prediction.quantize(Decimal("0.01")),
                        lower_revenue_uzs=max(Decimal(0), lower).quantize(
                            Decimal("0.01")
                        ),
                        upper_revenue_uzs=upper.quantize(Decimal("0.01")),
                        trend_component_uzs=trend_component.quantize(Decimal("0.01")),
                        seasonal_component_uzs=(prediction - trend_component).quantize(
                            Decimal("0.01")
                        ),
                        confidence_level=0.95,
                    )
                )

    session.add_all(monthly_rows)
    session.add_all(forecast_points)
    await session.flush()
    print(
        f"    {len(monthly_rows)} ta monthly revenue, "
        f"{len(forecast_runs)} ta forecast run, "
        f"{len(forecast_points)} ta forecast point qo'shildi"
    )


async def seed_viability_check(
    session: AsyncSession, categories: list[MCCCategory]
) -> None:
    print("  M-D1 Viability Check ma'lumotlari yozilmoqda...")

    existing = await session.execute(select(ViabilityCheckRun).limit(1))
    if existing.scalar() is not None:
        print("    Viability Check ma'lumotlari mavjud, o'tkazib yuborildi")
        return

    if not categories:
        print("    MCC kategoriyalar topilmadi, o'tkazib yuborildi")
        return

    sector_profiles = {
        "Oziq-ovqat": {
            "margin": 0.32,
            "variable": 0.68,
            "fixed": 0.22,
            "payroll": 0.13,
            "rent": 0.07,
            "marketing": 0.03,
            "revenue": 95_000_000,
            "volatility": 0.18,
            "growth": 0.014,
            "capex": 180_000_000,
            "failure": 0.32,
        },
        "Sog'liqni saqlash": {
            "margin": 0.42,
            "variable": 0.58,
            "fixed": 0.20,
            "payroll": 0.16,
            "rent": 0.06,
            "marketing": 0.02,
            "revenue": 80_000_000,
            "volatility": 0.12,
            "growth": 0.011,
            "capex": 220_000_000,
            "failure": 0.24,
        },
        "Kiyim-kechak": {
            "margin": 0.46,
            "variable": 0.54,
            "fixed": 0.26,
            "payroll": 0.12,
            "rent": 0.10,
            "marketing": 0.05,
            "revenue": 120_000_000,
            "volatility": 0.27,
            "growth": 0.010,
            "capex": 260_000_000,
            "failure": 0.38,
        },
        "Xizmatlar": {
            "margin": 0.55,
            "variable": 0.45,
            "fixed": 0.25,
            "payroll": 0.20,
            "rent": 0.07,
            "marketing": 0.04,
            "revenue": 60_000_000,
            "volatility": 0.22,
            "growth": 0.012,
            "capex": 140_000_000,
            "failure": 0.34,
        },
    }
    default_profile = {
        "margin": 0.40,
        "variable": 0.60,
        "fixed": 0.24,
        "payroll": 0.14,
        "rent": 0.08,
        "marketing": 0.04,
        "revenue": 85_000_000,
        "volatility": 0.23,
        "growth": 0.011,
        "capex": 200_000_000,
        "failure": 0.35,
    }

    benchmarks: list[SectorFinancialBenchmark] = []
    assumptions: list[ViabilityPlanAssumption] = []
    runs: list[ViabilityCheckRun] = []
    cashflow_months: list[ViabilityCashflowMonth] = []

    for idx, category in enumerate(categories[:10]):
        profile = sector_profiles.get(category.parent_category, default_profile)
        base_revenue = int(profile["revenue"] * random.uniform(0.82, 1.22))
        startup_capex = int(profile["capex"] * random.uniform(0.85, 1.20))
        gross_margin = round(profile["margin"] * random.uniform(0.94, 1.06), 3)
        variable_cost = round(max(0.1, 1 - gross_margin), 3)
        fixed_cost = int(base_revenue * profile["fixed"] * random.uniform(0.88, 1.12))
        rent = int(fixed_cost * profile["rent"] / profile["fixed"])
        payroll = int(fixed_cost * profile["payroll"] / profile["fixed"])
        marketing = int(fixed_cost * profile["marketing"] / profile["fixed"])
        utilities = int(fixed_cost * 0.08)
        other_fixed = max(0, fixed_cost - rent - payroll - marketing - utilities)
        initial_capital = int(startup_capex * random.uniform(1.25, 1.75))
        working_capital = max(0, initial_capital - startup_capex)
        loan_amount = int(startup_capex * random.uniform(0.15, 0.45))
        loan_payment = int(loan_amount / 24 * random.uniform(1.04, 1.14))
        lat, lon = rand_coord_near(*TASHKENT_CENTER, radius_km=4.0)
        seasonality_shift = random.randint(0, 11)

        existing_benchmark = await session.execute(
            select(SectorFinancialBenchmark).where(
                SectorFinancialBenchmark.mcc_code == category.mcc_code,
                SectorFinancialBenchmark.city == CITY,
                SectorFinancialBenchmark.data_year == 2026,
            )
        )
        if existing_benchmark.scalar() is None:
            benchmark = SectorFinancialBenchmark(
                mcc_code=category.mcc_code,
                niche=category.niche_name_uz,
                city=CITY,
                gross_margin_pct=gross_margin,
                variable_cost_pct=variable_cost,
                fixed_cost_ratio_pct=round(profile["fixed"], 3),
                payroll_cost_ratio_pct=round(profile["payroll"], 3),
                rent_cost_ratio_pct=round(profile["rent"], 3),
                marketing_cost_ratio_pct=round(profile["marketing"], 3),
                avg_monthly_revenue_uzs=Decimal(base_revenue),
                median_monthly_revenue_uzs=Decimal(int(base_revenue * 0.88)),
                revenue_volatility_pct=round(profile["volatility"], 3),
                monthly_growth_pct=round(profile["growth"], 4),
                startup_capex_p25_uzs=Decimal(int(startup_capex * 0.75)),
                startup_capex_median_uzs=Decimal(startup_capex),
                startup_capex_p75_uzs=Decimal(int(startup_capex * 1.35)),
                working_capital_months=round(random.uniform(2.5, 5.0), 1),
                two_year_failure_rate_pct=round(profile["failure"], 3),
                data_year=2026,
                data_source="synthetic_financial_model",
                notes={
                    "source": "seed_db.py",
                    "purpose": "M-D1 Viability Check test data",
                    "is_fake_data": True,
                },
            )
            session.add(benchmark)
            benchmarks.append(benchmark)

        assumption = ViabilityPlanAssumption(
            plan_name=f"{category.niche_name_uz} viability scenario #{idx + 1}",
            mcc_code=category.mcc_code,
            niche=category.niche_name_uz,
            city=CITY,
            lat=lat,
            lon=lon,
            radius_m=random.choice([1000.0, 2500.0, 5000.0]),
            initial_capital_uzs=Decimal(initial_capital),
            startup_capex_uzs=Decimal(startup_capex),
            working_capital_uzs=Decimal(working_capital),
            loan_amount_uzs=Decimal(loan_amount),
            monthly_loan_payment_uzs=Decimal(loan_payment),
            expected_monthly_revenue_uzs=Decimal(base_revenue),
            avg_ticket_uzs=Decimal(random.randint(35_000, 220_000)),
            expected_monthly_transactions=random.randint(450, 3500),
            gross_margin_pct=gross_margin,
            variable_cost_pct=variable_cost,
            monthly_fixed_cost_uzs=Decimal(fixed_cost),
            monthly_rent_uzs=Decimal(rent),
            monthly_payroll_uzs=Decimal(payroll),
            monthly_utilities_uzs=Decimal(utilities),
            monthly_marketing_uzs=Decimal(marketing),
            monthly_other_fixed_uzs=Decimal(other_fixed),
            monthly_revenue_growth_pct=round(profile["growth"], 4),
            revenue_volatility_pct=round(profile["volatility"], 3),
            tax_rate_pct=0.04,
            owner_draw_uzs=Decimal(random.randint(3_000_000, 12_000_000)),
            seasonality_profile={
                str(month): round(
                    1.10
                    if (month + seasonality_shift) % 12 in (3, 4, 10, 11)
                    else 0.94
                    if month in (1, 2)
                    else 1.0,
                    2,
                )
                for month in range(1, 13)
            },
            risk_assumptions={
                "rent_increase_probability": 0.18,
                "supplier_cost_shock_probability": 0.12,
                "competitor_entry_probability": 0.25,
                "monthly_revenue_std_pct": round(profile["volatility"], 3),
            },
            created_by="seed_db.py",
        )
        session.add(assumption)
        await session.flush()
        assumptions.append(assumption)

        cumulative_cash = Decimal(initial_capital - startup_capex)
        cumulative_p10 = cumulative_cash
        cumulative_p90 = cumulative_cash
        break_even_month = None
        worst_month_cash = cumulative_cash

        monthly_rows: list[ViabilityCashflowMonth] = []
        for month_idx in range(1, 25):
            month_date = add_months(date(2026, 4, 1), month_idx - 1)
            seasonality = Decimal(
                str(assumption.seasonality_profile[str(month_date.month)])
            )
            growth = Decimal(str((1 + profile["growth"]) ** (month_idx - 1)))
            expected_revenue = Decimal(base_revenue) * growth * seasonality
            p10_revenue = expected_revenue * Decimal("0.78")
            p90_revenue = expected_revenue * Decimal("1.24")
            variable_cost_uzs = expected_revenue * Decimal(str(variable_cost))
            tax_base = max(Decimal(0), expected_revenue - variable_cost_uzs)
            tax = tax_base * Decimal(str(assumption.tax_rate_pct))
            net_cashflow = (
                expected_revenue
                - variable_cost_uzs
                - Decimal(fixed_cost)
                - Decimal(loan_payment)
                - tax
                - assumption.owner_draw_uzs
            )
            cumulative_cash += net_cashflow
            cumulative_p10 += net_cashflow - (expected_revenue * Decimal("0.18"))
            cumulative_p90 += net_cashflow + (expected_revenue * Decimal("0.18"))
            worst_month_cash = min(worst_month_cash, cumulative_p10)
            if break_even_month is None and cumulative_cash >= Decimal(0):
                break_even_month = month_idx

            monthly_rows.append(
                ViabilityCashflowMonth(
                    run_id=0,
                    month_index=month_idx,
                    expected_revenue_uzs=expected_revenue.quantize(Decimal("0.01")),
                    p10_revenue_uzs=p10_revenue.quantize(Decimal("0.01")),
                    p90_revenue_uzs=p90_revenue.quantize(Decimal("0.01")),
                    variable_cost_uzs=variable_cost_uzs.quantize(Decimal("0.01")),
                    fixed_cost_uzs=Decimal(fixed_cost),
                    loan_payment_uzs=Decimal(loan_payment),
                    tax_uzs=tax.quantize(Decimal("0.01")),
                    net_cashflow_uzs=net_cashflow.quantize(Decimal("0.01")),
                    cumulative_cash_p10_uzs=cumulative_p10.quantize(Decimal("0.01")),
                    cumulative_cash_p50_uzs=cumulative_cash.quantize(Decimal("0.01")),
                    cumulative_cash_p90_uzs=cumulative_p90.quantize(Decimal("0.01")),
                    probability_negative_cash=round(
                        min(0.95, max(0.05, 0.15 + month_idx * 0.015)),
                        3,
                    ),
                    is_break_even_month=False,
                )
            )

        runway_months = 24.0 if worst_month_cash >= 0 else random.uniform(6.0, 18.0)
        survival_probability = max(
            0.05,
            min(0.97, 1 - profile["failure"] + random.uniform(-0.10, 0.12)),
        )
        viability_score = round(survival_probability * 100, 1)
        recommendation = (
            "approve"
            if viability_score >= 72
            else "review"
            if viability_score >= 52
            else "reject"
        )
        min_required_capital = max(
            Decimal(0),
            abs(worst_month_cash) + Decimal(fixed_cost * 2),
        )

        run = ViabilityCheckRun(
            assumption_id=assumption.id,
            mcc_code=category.mcc_code,
            niche=category.niche_name_uz,
            city=CITY,
            simulation_months=24,
            monte_carlo_iterations=2000,
            random_seed=SEED + idx,
            break_even_month=break_even_month,
            runway_months=round(runway_months, 1),
            survival_probability_24m=round(survival_probability, 3),
            cash_out_probability_24m=round(1 - survival_probability, 3),
            probability_break_even_24m=round(
                0.85 if break_even_month is not None else 0.35,
                3,
            ),
            median_final_cash_uzs=cumulative_cash.quantize(Decimal("0.01")),
            p10_final_cash_uzs=cumulative_p10.quantize(Decimal("0.01")),
            p90_final_cash_uzs=cumulative_p90.quantize(Decimal("0.01")),
            worst_month_cash_uzs=worst_month_cash.quantize(Decimal("0.01")),
            min_required_capital_uzs=min_required_capital.quantize(Decimal("0.01")),
            viability_score=viability_score,
            recommendation=recommendation,
            confidence_score=round(random.uniform(0.72, 0.91), 2),
            analysis_summary=(
                f"{category.niche_name_uz} uchun 24 oylik fake Monte Carlo "
                "viability natijasi: break-even, runway va survival probability."
            ),
            calc_metadata={
                "source": "seed_db.py",
                "method": "financial_model_monte_carlo_mock",
                "is_fake_data": True,
                "iterations": 2000,
            },
        )
        session.add(run)
        await session.flush()
        runs.append(run)

        for row in monthly_rows:
            row.run_id = run.id
            row.is_break_even_month = row.month_index == break_even_month
        cashflow_months.extend(monthly_rows)

    session.add_all(cashflow_months)
    await session.flush()
    print(
        f"    {len(benchmarks)} ta benchmark, "
        f"{len(assumptions)} ta assumption, "
        f"{len(runs)} ta run, "
        f"{len(cashflow_months)} ta cashflow oy qo'shildi"
    )


def months_between(start: date, end: date) -> int:
    return max(0, (end.year - start.year) * 12 + end.month - start.month)


def churn_risk_bucket(probability: float) -> str:
    if probability >= 0.70:
        return "critical"
    if probability >= 0.45:
        return "high"
    if probability >= 0.25:
        return "medium"
    return "low"


async def seed_churn_prediction(session: AsyncSession) -> None:
    print("  M-E2 Churn Prediction ma'lumotlari yozilmoqda...")

    existing = await session.execute(select(ChurnPredictionRun).limit(1))
    if existing.scalar() is not None:
        print("    Churn Prediction ma'lumotlari mavjud, o'tkazib yuborildi")
        return

    result = await session.execute(select(Business).order_by(Business.id).limit(80))
    businesses = list(result.scalars().all())
    if not businesses:
        print("    Business ma'lumotlari topilmadi, o'tkazib yuborildi")
        return

    feature_names = [
        "business_age_months",
        "revenue_trend_6m_pct",
        "revenue_volatility_12m_pct",
        "revenue_drop_last_3m_pct",
        "zero_revenue_months_12m",
        "tx_count_trend_6m_pct",
        "inactive_days_last_90d",
        "competitor_density_score",
        "nearby_closed_businesses_24m",
        "district_failure_rate_24m_pct",
        "macro_risk_score",
        "seasonality_risk_score",
    ]
    model_version = ChurnModelVersion(
        model_name="xgboost_smb_churn",
        model_version="mock-v1-2026-04",
        algorithm="XGBoost",
        training_sample_size=50_000,
        positive_label_rate=0.28,
        auc_roc=0.86,
        auc_pr=0.62,
        f1_score=0.71,
        calibration_error=0.045,
        feature_names=feature_names,
        hyperparameters={
            "max_depth": 5,
            "n_estimators": 450,
            "learning_rate": 0.045,
            "subsample": 0.85,
            "colsample_bytree": 0.80,
            "objective": "binary:logistic",
        },
        training_period_start=date(2022, 1, 1),
        training_period_end=date(2026, 3, 31),
        is_active=True,
    )
    session.add(model_version)
    await session.flush()

    as_of_date = date(2026, 4, 25)
    snapshots: list[ChurnFeatureSnapshot] = []
    runs: list[ChurnPredictionRun] = []
    risk_factors: list[ChurnRiskFactor] = []
    closure_reasons = [
        "revenue_drop",
        "low_transaction_activity",
        "high_competition",
        "rent_pressure",
        "owner_exit",
    ]

    for business in businesses:
        age_months = months_between(business.registered_date, as_of_date)
        is_closed = business.closed_date is not None or not business.is_active
        if is_closed and business.closed_date is None:
            earliest_close = business.registered_date + timedelta(days=180)
            business.closed_date = rand_date(earliest_close, as_of_date)
        business.last_observed_active_date = business.closed_date or as_of_date
        business.closure_reason = (
            business.closure_reason or random.choice(closure_reasons)
            if is_closed
            else None
        )
        business.closure_confidence_score = (
            business.closure_confidence_score or round(random.uniform(0.75, 0.97), 2)
            if is_closed
            else None
        )

        base_revenue = float(business.monthly_revenue_est_uzs or Decimal("15000000"))
        weak_signal = 1.0 if is_closed else random.uniform(0.0, 0.7)
        revenue_drop = round(random.uniform(0.10, 0.65) * weak_signal, 3)
        revenue_trend = round(random.uniform(-0.55, 0.18) * (0.4 + weak_signal), 3)
        revenue_volatility = round(random.uniform(0.08, 0.55) + weak_signal * 0.12, 3)
        zero_months = random.randint(2, 8) if is_closed else random.randint(0, 3)
        tx_trend = round(revenue_trend * random.uniform(0.75, 1.25), 3)
        inactive_days = random.randint(25, 90) if is_closed else random.randint(0, 35)
        active_days = max(0, 90 - inactive_days)
        competitor_count = random.randint(3, 45)
        competitor_density = round(min(1.0, competitor_count / 40), 3)
        closed_nearby = random.randint(0, 12)
        district_failure = round(random.uniform(0.12, 0.48), 3)
        macro_risk = round(random.uniform(0.10, 0.55), 3)
        seasonality_risk = round(random.uniform(0.05, 0.45), 3)
        data_quality = round(random.uniform(0.70, 0.95), 3)

        revenue_12m = Decimal(str(round(base_revenue * random.uniform(0.85, 1.10), 2)))
        revenue_6m = Decimal(str(round(base_revenue * (1 + revenue_trend / 2), 2)))
        revenue_3m = Decimal(str(round(base_revenue * (1 - revenue_drop), 2)))
        tx_12m = random.uniform(120, 2600)
        tx_3m = max(1.0, tx_12m * (1 + tx_trend))
        avg_ticket_3m = revenue_3m / Decimal(str(max(tx_3m, 1)))
        ticket_change = round(random.uniform(-0.25, 0.18), 3)

        risk_components = {
            "revenue_drop_last_3m_pct": revenue_drop * 0.30,
            "negative_revenue_trend_6m": max(0.0, -revenue_trend) * 0.24,
            "inactive_days_last_90d": inactive_days / 90 * 0.18,
            "revenue_volatility_12m_pct": revenue_volatility * 0.14,
            "competitor_density_score": competitor_density * 0.10,
            "district_failure_rate_24m_pct": district_failure * 0.08,
            "zero_revenue_months_12m": zero_months / 12 * 0.18,
        }
        raw_probability = 0.08 + sum(risk_components.values())
        if is_closed:
            raw_probability += 0.22
        closure_probability = round(max(0.02, min(0.96, raw_probability)), 4)
        survival_probability = round(1 - closure_probability, 4)
        risk_bucket = churn_risk_bucket(closure_probability)
        risk_score = round(closure_probability * 100, 1)

        target_closed_within_24m = None
        if business.closed_date:
            target_closed_within_24m = (
                months_between(business.registered_date, business.closed_date) <= 24
            )

        snapshot = ChurnFeatureSnapshot(
            business_id=business.id,
            mcc_code=business.mcc_code,
            niche=business.niche,
            city=business.city,
            district=business.district,
            lat=business.lat,
            lon=business.lon,
            radius_m=1000.0,
            as_of_date=as_of_date,
            business_age_months=age_months,
            employee_count_est=business.employee_count_est,
            area_sqm=business.area_sqm,
            revenue_3m_avg_uzs=revenue_3m,
            revenue_6m_avg_uzs=revenue_6m,
            revenue_12m_avg_uzs=revenue_12m,
            revenue_trend_6m_pct=revenue_trend,
            revenue_volatility_12m_pct=revenue_volatility,
            revenue_drop_last_3m_pct=revenue_drop,
            zero_revenue_months_12m=zero_months,
            tx_count_3m_avg=round(tx_3m, 1),
            tx_count_12m_avg=round(tx_12m, 1),
            tx_count_trend_6m_pct=tx_trend,
            avg_ticket_3m_uzs=avg_ticket_3m.quantize(Decimal("0.01")),
            avg_ticket_change_6m_pct=ticket_change,
            active_days_last_90d=active_days,
            inactive_days_last_90d=inactive_days,
            online_share_12m_pct=round(random.uniform(0.03, 0.35), 3),
            competitor_count_radius=competitor_count,
            competitor_density_score=competitor_density,
            nearby_closed_businesses_24m=closed_nearby,
            district_failure_rate_24m_pct=district_failure,
            macro_risk_score=macro_risk,
            seasonality_risk_score=seasonality_risk,
            data_quality_score=data_quality,
            target_closed_within_24m=target_closed_within_24m,
            target_closed_date=business.closed_date,
            raw_features={
                "source": "seed_db.py",
                "is_fake_data": True,
                "risk_components": risk_components,
            },
        )
        session.add(snapshot)
        await session.flush()
        snapshots.append(snapshot)

        top_factors = sorted(
            risk_components.items(),
            key=lambda item: item[1],
            reverse=True,
        )[:3]
        top_names = [name for name, _ in top_factors]
        run = ChurnPredictionRun(
            business_id=business.id,
            feature_snapshot_id=snapshot.id,
            model_version_id=model_version.id,
            mcc_code=business.mcc_code,
            niche=business.niche,
            city=business.city,
            as_of_date=as_of_date,
            prediction_horizon_months=24,
            closure_probability_24m=closure_probability,
            survival_probability_24m=survival_probability,
            risk_bucket=risk_bucket,
            risk_score=risk_score,
            confidence_score=round(data_quality * random.uniform(0.88, 0.98), 3),
            top_factor_1=top_names[0],
            top_factor_2=top_names[1],
            top_factor_3=top_names[2],
            prediction_summary=(
                f"{business.niche} biznesi uchun 24 oy ichida yopilish ehtimoli "
                f"{closure_probability:.0%}. Top risklar: "
                f"{', '.join(top_names)}."
            ),
            calc_metadata={
                "source": "seed_db.py",
                "method": "xgboost_mock_scorecard",
                "model_family": "XGBoost",
                "is_fake_data": True,
            },
        )
        session.add(run)
        await session.flush()
        runs.append(run)

        factor_labels = {
            "revenue_drop_last_3m_pct": "So'nggi 3 oy revenue pasayishi",
            "negative_revenue_trend_6m": "6 oylik revenue trend manfiy",
            "inactive_days_last_90d": "So'nggi 90 kunda faol bo'lmagan kunlar",
            "revenue_volatility_12m_pct": "Revenue volatility yuqori",
            "competitor_density_score": "Raqobatchilar zichligi yuqori",
            "district_failure_rate_24m_pct": "Tuman bo'yicha yopilish darajasi",
            "zero_revenue_months_12m": "12 oy ichida revenue bo'lmagan oylar",
        }
        for rank, (factor_name, impact) in enumerate(top_factors, start=1):
            risk_factors.append(
                ChurnRiskFactor(
                    prediction_run_id=run.id,
                    rank=rank,
                    factor_name=factor_name,
                    factor_group=(
                        "revenue"
                        if "revenue" in factor_name or "tx" in factor_name
                        else "competition"
                        if "competitor" in factor_name or "district" in factor_name
                        else "activity"
                    ),
                    factor_value=str(round(impact, 4)),
                    baseline_value="mock_sector_baseline",
                    impact_score=round(impact, 4),
                    direction="increases_risk",
                    explanation=factor_labels[factor_name],
                )
            )

    session.add_all(risk_factors)
    await session.flush()
    print(
        f"    1 ta model version, {len(snapshots)} ta feature snapshot, "
        f"{len(runs)} ta prediction run, "
        f"{len(risk_factors)} ta risk factor qo'shildi"
    )


async def clear_tables(session: AsyncSession) -> None:
    print("  Jadvallar tozalanmoqda...")
    # Foreign key tartibiga rioya qilib o'chirish
    for table in [
        "churn_risk_factors",
        "churn_prediction_runs",
        "churn_feature_snapshots",
        "churn_model_versions",
        "viability_cashflow_months",
        "viability_check_runs",
        "viability_plan_assumptions",
        "sector_financial_benchmarks",
        "demand_forecast_points",
        "demand_forecast_runs",
        "niche_monthly_revenues",
        "market_size_estimates",
        "market_benchmarks",
        "customer_segments",
        "points_of_interest",
        "population_zones",
        "businesses",
        "transactions",
        "mcc_categories",
    ]:
        await session.execute(text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE"))
    print("    Barcha jadvallar tozalandi")


async def has_existing_data(session: AsyncSession) -> bool:
    result = await session.execute(select(MCCCategory).limit(1))
    return result.scalar() is not None


async def main(
    clear: bool = False,
    forecast_only: bool = False,
    viability_only: bool = False,
    churn_only: bool = False,
) -> None:
    print(f"\n=== Fake data seed ({CITY}) ===\n")

    engine = create_async_engine(settings.database_url, echo=False)
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with Session() as session:
        async with session.begin():
            if churn_only:
                await seed_churn_prediction(session)
                return

            if viability_only:
                stmt = select(MCCCategory).order_by(MCCCategory.id)
                result = await session.execute(stmt)
                categories = list(result.scalars().all())
                if not categories:
                    print(
                        "XATO: MCC kategoriyalar topilmadi. "
                        "Avval umumiy seedni ishga tushiring."
                    )
                    return
                await seed_viability_check(session, categories)
                return

            if forecast_only:
                stmt = select(MCCCategory).order_by(MCCCategory.id)
                result = await session.execute(stmt)
                categories = list(result.scalars().all())
                if not categories:
                    print(
                        "XATO: MCC kategoriyalar topilmadi. "
                        "Avval umumiy seedni ishga tushiring."
                    )
                    return
                await seed_demand_forecasting(session, categories)
                return

            if not clear and await has_existing_data(session):
                print(
                    "XATO: Databazada allaqachon ma'lumotlar mavjud.\n"
                    "Tozalab qayta to'ldirish uchun --clear flagini ishlating:\n\n"
                    "    uv run python scripts/seed_db.py --clear\n"
                )
                return

            if clear:
                await clear_tables(session)

            categories = await seed_mcc_categories(session)
            mcc_codes = [c.mcc_code for c in categories]
            mcc_data_clean = [
                (categories[i].mcc_code, *MCC_DATA[i][1:])
                for i in range(len(categories))
            ]

            await seed_transactions(session, mcc_codes, count=5000)
            await seed_businesses(session, mcc_data_clean)
            await seed_market_benchmarks(session, mcc_data_clean)
            await seed_population_zones(session)
            await seed_poi(session)
            await seed_customer_segments(session)
            await seed_market_size_estimates(session, mcc_data_clean)
            await seed_demand_forecasting(session, categories)
            await seed_viability_check(session, categories)
            await seed_churn_prediction(session)

    await engine.dispose()
    print("\n=== Seed muvaffaqiyatli yakunlandi! ===\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fake data seeder")
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Seed qilishdan oldin barcha jadvallarni tozalash",
    )
    parser.add_argument(
        "--forecast-only",
        action="store_true",
        help="Faqat M-B1 demand forecasting fake data jadvallarini to'ldirish",
    )
    parser.add_argument(
        "--viability-only",
        action="store_true",
        help="Faqat M-D1 viability check fake data jadvallarini to'ldirish",
    )
    parser.add_argument(
        "--churn-only",
        action="store_true",
        help="Faqat M-E2 churn prediction fake data jadvallarini to'ldirish",
    )
    args = parser.parse_args()
    asyncio.run(
        main(
            clear=args.clear,
            forecast_only=args.forecast_only,
            viability_only=args.viability_only,
            churn_only=args.churn_only,
        )
    )
