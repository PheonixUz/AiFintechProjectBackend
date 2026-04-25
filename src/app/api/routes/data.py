"""
Market analiz uchun kerakli ma'lumotlarni qaytaruvchi GET APIlar.

GET /api/v1/data/niches              — MCC kategoriyalar ro'yxati
GET /api/v1/data/benchmarks          — Nisha benchmarklari
GET /api/v1/data/competitors         — Raqobatchilar (radius bo'yicha)
GET /api/v1/data/transactions        — Tranzaksiya statistikasi
GET /api/v1/data/population          — Aholi zonalari (radius bo'yicha)
GET /api/v1/data/poi                 — Qiziqish nuqtalari (radius bo'yicha)
GET /api/v1/data/customer-segments   — Mijoz segmentlari (radius bo'yicha)
GET /api/v1/data/market-estimates    — Saqlangan bozor tahminlari
"""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.db.repositories.data_repo import DataRepository
from app.schemas.data import (
    BenchmarkOut,
    CompetitorListOut,
    CompetitorOut,
    CustomerSegmentListOut,
    CustomerSegmentOut,
    MarketEstimateOut,
    MCCCategoryOut,
    POIListOut,
    POIOut,
    PopulationListOut,
    PopulationZoneOut,
    TransactionMonthOut,
    TransactionSummaryOut,
)

router = APIRouter(prefix="/data", tags=["Data: Market ma'lumotlari"])


# ── MCC Kategoriyalar ──────────────────────────────────────────────────────────

@router.get(
    "/niches",
    response_model=list[MCCCategoryOut],
    summary="Barcha biznes nishalari (MCC kategoriyalar)",
    description="Tizimda mavjud barcha MCC kategoriyalar va ularning o'zbekcha nomlari.",
)
async def get_niches(
    active_only: bool = Query(default=True, description="Faqat faol kategoriyalar"),
    parent_category: str | None = Query(default=None, description="Yuqori kategoriya filtri"),
    session: AsyncSession = Depends(get_session),
) -> list[MCCCategoryOut]:
    repo = DataRepository(session)
    if parent_category:
        categories = await repo.get_mcc_by_parent(parent_category)
    else:
        categories = await repo.get_mcc_categories(active_only=active_only)
    return [MCCCategoryOut.model_validate(c) for c in categories]


# ── Benchmarklar ───────────────────────────────────────────────────────────────

@router.get(
    "/benchmarks",
    response_model=list[BenchmarkOut],
    summary="Nisha sanoat benchmarklari",
    description=(
        "Berilgan shahar va nisha uchun o'rtacha daromad, margin, xodimlar soni "
        "va o'sish ko'rsatkichlarini qaytaradi."
    ),
)
async def get_benchmarks(
    city: str = Query(default="Toshkent", description="Shahar nomi"),
    mcc_code: str | None = Query(default=None, description="MCC kod (4 raqam)"),
    niche: str | None = Query(default=None, description="Biznes nishasi (masalan: restoran)"),
    session: AsyncSession = Depends(get_session),
) -> list[BenchmarkOut]:
    repo = DataRepository(session)
    benchmarks = await repo.get_benchmarks(city=city, mcc_code=mcc_code, niche=niche)
    return [BenchmarkOut.model_validate(b) for b in benchmarks]


# ── Raqobatchilar ──────────────────────────────────────────────────────────────

@router.get(
    "/competitors",
    response_model=CompetitorListOut,
    summary="Radius ichidagi raqobatchilar",
    description=(
        "Berilgan koordinata va radius ichidagi faol raqobatchilarni "
        "masofasi bilan birga qaytaradi."
    ),
)
async def get_competitors(
    niche: str = Query(..., description="Biznes nishasi (masalan: restoran)"),
    lat: float = Query(..., ge=-90, le=90, description="Kenglik (latitude)"),
    lon: float = Query(..., ge=-180, le=180, description="Uzunlik (longitude)"),
    radius_m: float = Query(default=1000, ge=100, le=10_000, description="Radius (metr)"),
    active_only: bool = Query(default=True, description="Faqat faol bizneslar"),
    session: AsyncSession = Depends(get_session),
) -> CompetitorListOut:
    repo = DataRepository(session)
    results = await repo.get_competitors(
        niche=niche, lat=lat, lon=lon, radius_m=radius_m, active_only=active_only
    )
    competitors = []
    for r in results:
        out = CompetitorOut.model_validate(r["business"])
        out = out.model_copy(update={"distance_m": r["distance_m"]})
        competitors.append(out)
    return CompetitorListOut(
        niche=niche,
        lat=lat,
        lon=lon,
        radius_m=radius_m,
        total_count=len(competitors),
        competitors=competitors,
    )


# ── Tranzaksiya statistikasi ───────────────────────────────────────────────────

@router.get(
    "/transactions",
    response_model=TransactionSummaryOut,
    summary="MCC kategoriya bo'yicha tranzaksiya statistikasi",
    description=(
        "Berilgan MCC kod va shahar uchun yillik tranzaksiya yig'indisi va "
        "oyma-oy taqsimotini qaytaradi. TAM hisoblash uchun asosiy ma'lumot."
    ),
)
async def get_transactions(
    mcc_code: str = Query(..., min_length=4, max_length=4, description="MCC kod (4 raqam)"),
    city: str = Query(default="Toshkent", description="Shahar nomi"),
    year: int = Query(default=2025, ge=2020, le=2030, description="Yil"),
    session: AsyncSession = Depends(get_session),
) -> TransactionSummaryOut:
    repo = DataRepository(session)
    monthly = await repo.get_transaction_monthly_breakdown(
        mcc_code=mcc_code, city=city, year=year
    )
    annual_total = sum(m["total_uzs"] for m in monthly)
    return TransactionSummaryOut(
        mcc_code=mcc_code,
        city=city,
        year=year,
        annual_total_uzs=annual_total,
        monthly_breakdown=[TransactionMonthOut(**m) for m in monthly],
        months_with_data=len(monthly),
    )


# ── Aholi zonalari ─────────────────────────────────────────────────────────────

@router.get(
    "/population",
    response_model=PopulationListOut,
    summary="Radius ichidagi aholi zonalari",
    description=(
        "Berilgan koordinata va radius ichidagi aholi zonalarini qaytaradi. "
        "Bottom-up TAM hisoblash uchun: aholi ×침투stavka × o'rtacha xarajat."
    ),
)
async def get_population(
    lat: float = Query(..., ge=-90, le=90, description="Kenglik (latitude)"),
    lon: float = Query(..., ge=-180, le=180, description="Uzunlik (longitude)"),
    radius_m: float = Query(default=1000, ge=100, le=20_000, description="Radius (metr)"),
    city: str | None = Query(default=None, description="Shahar nomi filtri"),
    session: AsyncSession = Depends(get_session),
) -> PopulationListOut:
    repo = DataRepository(session)
    zones = await repo.get_population_zones(lat=lat, lon=lon, radius_m=radius_m, city=city)
    zone_outs = [PopulationZoneOut.model_validate(z) for z in zones]
    total_pop = sum(z.total_population for z in zone_outs)
    return PopulationListOut(
        lat=lat,
        lon=lon,
        radius_m=radius_m,
        zones_count=len(zone_outs),
        total_population=total_pop,
        zones=zone_outs,
    )


# ── POI ────────────────────────────────────────────────────────────────────────

@router.get(
    "/poi",
    response_model=POIListOut,
    summary="Radius ichidagi qiziqish nuqtalari (POI)",
    description=(
        "Bozor, masjid, maktab, savdo markazi kabi qiziqish nuqtalarini "
        "masofasi bilan birga qaytaradi. M-C1 lokatsiya skori uchun."
    ),
)
async def get_poi(
    lat: float = Query(..., ge=-90, le=90, description="Kenglik (latitude)"),
    lon: float = Query(..., ge=-180, le=180, description="Uzunlik (longitude)"),
    radius_m: float = Query(default=500, ge=100, le=5_000, description="Radius (metr)"),
    poi_type: str | None = Query(
        default=None,
        description="POI turi: market, mosque, school, mall, park, hospital, university, transport_hub",
    ),
    city: str | None = Query(default=None, description="Shahar nomi filtri"),
    session: AsyncSession = Depends(get_session),
) -> POIListOut:
    repo = DataRepository(session)
    results = await repo.get_pois(
        lat=lat, lon=lon, radius_m=radius_m, poi_type=poi_type, city=city
    )
    pois = []
    for r in results:
        out = POIOut.model_validate(r["poi"])
        out = out.model_copy(update={"distance_m": r["distance_m"]})
        pois.append(out)
    return POIListOut(
        lat=lat,
        lon=lon,
        radius_m=radius_m,
        poi_type=poi_type,
        total_count=len(pois),
        pois=pois,
    )


# ── Mijoz segmentlari ──────────────────────────────────────────────────────────

@router.get(
    "/customer-segments",
    response_model=CustomerSegmentListOut,
    summary="Radius ichidagi mijoz segmentlari",
    description=(
        "Berilgan koordinata atrofidagi mijoz segmentlarini qaytaradi. "
        "SOM hisoblashda target segment penetration rate uchun ishlatiladi."
    ),
)
async def get_customer_segments(
    lat: float = Query(..., ge=-90, le=90, description="Kenglik (latitude)"),
    lon: float = Query(..., ge=-180, le=180, description="Uzunlik (longitude)"),
    radius_m: float = Query(default=1000, ge=100, le=10_000, description="Radius (metr)"),
    city: str | None = Query(default=None, description="Shahar nomi filtri"),
    session: AsyncSession = Depends(get_session),
) -> CustomerSegmentListOut:
    repo = DataRepository(session)
    segments = await repo.get_customer_segments(lat=lat, lon=lon, radius_m=radius_m, city=city)
    seg_outs = [CustomerSegmentOut.model_validate(s) for s in segments]
    total_customers = sum(s.estimated_count for s in seg_outs)
    return CustomerSegmentListOut(
        lat=lat,
        lon=lon,
        radius_m=radius_m,
        segments_count=len(seg_outs),
        total_customers_est=total_customers,
        segments=seg_outs,
    )


# ── Bozor tahminlari ───────────────────────────────────────────────────────────

@router.get(
    "/market-estimates",
    response_model=list[MarketEstimateOut],
    summary="Saqlangan TAM/SAM/SOM tahminlari",
    description=(
        "Oldingi hisoblashlardan saqlangan bozor tahminlarini qaytaradi. "
        "Bir xil so'rovlar uchun qayta hisoblashdan saqlanish uchun ishlatiladi."
    ),
)
async def get_market_estimates(
    niche: str = Query(..., description="Biznes nishasi"),
    city: str | None = Query(default=None, description="Shahar nomi filtri"),
    limit: int = Query(default=10, ge=1, le=50, description="Natijalar soni"),
    session: AsyncSession = Depends(get_session),
) -> list[MarketEstimateOut]:
    repo = DataRepository(session)
    estimates = await repo.get_market_estimates(niche=niche, city=city, limit=limit)
    return [MarketEstimateOut.model_validate(e) for e in estimates]


@router.get(
    "/market-estimates/by-location",
    response_model=MarketEstimateOut | None,
    summary="Lokatsiya bo'yicha TAM/SAM/SOM tahmini",
    description="Berilgan koordinata, radius va nisha uchun eng so'nggi saqlangan tahminni qaytaradi.",
)
async def get_market_estimate_by_location(
    niche: str = Query(..., description="Biznes nishasi"),
    lat: float = Query(..., ge=-90, le=90, description="Kenglik (latitude)"),
    lon: float = Query(..., ge=-180, le=180, description="Uzunlik (longitude)"),
    radius_m: float = Query(default=1000, ge=100, le=10_000, description="Radius (metr)"),
    calculation_date: date | None = Query(default=None, description="Hisoblash sanasi (YYYY-MM-DD)"),
    session: AsyncSession = Depends(get_session),
) -> MarketEstimateOut | None:
    repo = DataRepository(session)
    estimate = await repo.get_market_estimate_by_location(
        niche=niche, lat=lat, lon=lon, radius_m=radius_m, calculation_date=calculation_date
    )
    if estimate is None:
        return None
    return MarketEstimateOut.model_validate(estimate)
