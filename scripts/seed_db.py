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
from app.db.models.customer import CustomerSegment
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
    ("5411", "Grocery Stores", "Oziq-ovqat do'koni", "Продуктовый магазин", "Oziq-ovqat"),
    ("5812", "Eating Places, Restaurants", "Restoran", "Ресторан", "Oziq-ovqat"),
    ("5814", "Fast Food Restaurants", "Tez ovqat", "Фаст-фуд", "Oziq-ovqat"),
    ("5912", "Drug Stores and Pharmacies", "Dorixona", "Аптека", "Sog'liqni saqlash"),
    ("7011", "Hotels and Motels", "Mehmonxona", "Гостиница", "Xizmatlar"),
    ("5621", "Women's Ready-To-Wear Stores", "Ayollar kiyimi", "Женская одежда", "Kiyim-kechak"),
    ("5611", "Men's Clothing Stores", "Erkaklar kiyimi", "Мужская одежда", "Kiyim-kechak"),
    ("5945", "Hobby, Toy, and Game Shops", "O'yinchoq do'koni", "Игрушки", "Ko'ngilochar"),
    ("7230", "Beauty Shops", "Go'zallik saloni", "Салон красоты", "Xizmatlar"),
    ("7011", "Fitness Centers", "Sport zali", "Фитнес-зал", "Sport"),
    ("5251", "Hardware Stores", "Qurilish mollari", "Стройматериалы", "Qurilish"),
    ("5065", "Electronic Parts", "Elektronika do'koni", "Электроника", "Texnika"),
    ("7542", "Car Washes", "Avtomobil yuvish", "Автомойка", "Avtomobil xizmatlari"),
    ("5441", "Candy Stores", "Shirinliklar do'koni", "Кондитерская", "Oziq-ovqat"),
    ("5999", "Other Retail", "Boshqa savdo", "Прочая торговля", "Savdo"),
]


# ─── Yordamchi funksiyalar ────────────────────────────────────────────────────

def rand_coord_near(lat: float, lon: float, radius_km: float = 2.0) -> tuple[float, float]:
    dlat = random.uniform(-radius_km / 111, radius_km / 111)
    dlon = random.uniform(-radius_km / 85, radius_km / 85)
    return round(lat + dlat, 6), round(lon + dlon, 6)


def rand_date(start: date, end: date) -> date:
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta))


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


async def seed_transactions(session: AsyncSession, mcc_codes: list[str], count: int = 5000) -> None:
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
                avg_monthly_spending_uzs=Decimal(int(avg_income * random.uniform(0.60, 0.75))),
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
            count = random.randint(1, 4) if poi_type in ("mosque", "school", "transport_hub") else 1
            for k in range(count):
                lat, lon = rand_coord_near(dlat, dlon, 2.5)
                capacity = random.randint(cap_min, cap_max)
                p = PointOfInterest(
                    name=f"{base_name} ({district_name}){' #' + str(k + 1) if count > 1 else ''}",
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


async def seed_market_size_estimates(session: AsyncSession, mcc_data: list[tuple]) -> None:
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

async def clear_tables(session: AsyncSession) -> None:
    print("  Jadvallar tozalanmoqda...")
    # Foreign key tartibiga rioya qilib o'chirish
    for table in [
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


async def main(clear: bool = False) -> None:
    print(f"\n=== Fake data seed ({CITY}) ===\n")

    engine = create_async_engine(settings.database_url, echo=False)
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with Session() as session:
        async with session.begin():
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

    await engine.dispose()
    print("\n=== Seed muvaffaqiyatli yakunlandi! ===\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fake data seeder")
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Seed qilishdan oldin barcha jadvallarni tozalash",
    )
    args = parser.parse_args()
    asyncio.run(main(clear=args.clear))
