"""
M-A1 Market Sizing uchun DB ma'lumot olish funksiyasi.

Faqat shu fayl DB ga murojaat qiladi — algorithm funksiyalari emas.
"""

from datetime import date
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.market_repo import MarketRepository

# Shahar miqyosidagi raqobatchi qidirish uchun standart radius
_CITY_RADIUS_M = 15_000


async def execute_get_market_data(
    session: AsyncSession,
    *,
    mcc_code: str,
    niche: str,
    lat: float,
    lon: float,
    radius_m: float,
    city: str,
    year: int,
) -> dict:
    """
    MarketRepository orqali M-A1 uchun barcha zarur ma'lumotlarni to'playdi.

    Qaytadi: algorithm va agent uchun tayyor dict.
    """
    repo = MarketRepository(session)

    # async session bir vaqtda bir so'rovni qo'llab-quvvatlaydi → ketma-ket
    tam = await repo.get_tam(mcc_code, city, year)

    sam_rows = await repo.get_sam_raw(mcc_code, lat, lon, radius_m, year)
    sam = sum((r["amount_uzs"] for r in sam_rows), Decimal(0))
    transaction_sample_size = len(sam_rows)

    competitor_count_radius = await repo.get_competitor_count(niche, lat, lon, radius_m)
    competitor_count_city = await repo.get_competitor_count(
        niche, lat, lon, _CITY_RADIUS_M
    )

    benchmark = await repo.get_benchmarks(mcc_code, city)
    cached = await repo.get_cached_estimate(niche, lat, lon, radius_m, date.today())

    result: dict = {
        "tam_transactions_uzs": str(tam),
        "sam_transactions_uzs": str(sam),
        "transaction_sample_size": transaction_sample_size,
        "competitor_count_radius": competitor_count_radius,
        "competitor_count_city": competitor_count_city,
        "cached_estimate": None,
        "benchmark": None,
    }

    if cached:
        result["cached_estimate"] = {
            "tam_uzs": str(cached.tam_uzs),
            "sam_uzs": str(cached.sam_uzs),
            "som_uzs": str(cached.som_uzs),
            "confidence_score": cached.confidence_score,
            "calculation_date": cached.calculation_date.isoformat(),
        }

    if benchmark:
        result["benchmark"] = {
            "avg_monthly_revenue_uzs": str(benchmark.avg_monthly_revenue_uzs),
            "median_monthly_revenue_uzs": str(benchmark.median_monthly_revenue_uzs),
            "gross_margin_pct": benchmark.gross_margin_pct,
            "annual_growth_rate_pct": benchmark.annual_growth_rate_pct,
            "avg_employee_count": benchmark.avg_employee_count,
        }

    return result
