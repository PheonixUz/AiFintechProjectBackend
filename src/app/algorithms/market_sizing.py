"""
M-A1 Market Sizing — Bayesian regression + bottom-up.

Kirish: bank tranzaksiya ma'lumotlari + sanoat benchmarklari
Chiqish: TAM / SAM / SOM (UZS, yillik) ishonch oralig'i bilan

Metodologiya:
  Bottom-up  : raqobatchilar_soni × o'rtacha_oylik_daromad × 12
  Top-down   : bank tranzaksiyalari yig'indisi (haqiqiy ma'lumot)
  Bayesian   : tranzaksiya namuna hajmiga qarab og'irlik bilan birlashtirish
"""

from dataclasses import dataclass, field
from decimal import Decimal


@dataclass
class MarketSizingInput:
    tam_transactions_uzs: Decimal
    sam_transactions_uzs: Decimal
    competitor_count_city: int
    competitor_count_radius: int
    avg_monthly_revenue_uzs: Decimal
    median_monthly_revenue_uzs: Decimal
    annual_growth_rate_pct: float
    gross_margin_pct: float
    transaction_sample_size: int
    # 0.5–1.5: lokatsiya va biznes sifati tuzatish koeffitsienti
    quality_factor: float = 1.0


@dataclass
class MarketSizingResult:
    tam_uzs: Decimal
    sam_uzs: Decimal
    som_uzs: Decimal
    tam_low_uzs: Decimal
    tam_high_uzs: Decimal
    sam_low_uzs: Decimal
    sam_high_uzs: Decimal
    som_low_uzs: Decimal
    som_high_uzs: Decimal
    market_share_pct: float
    market_growth_rate_pct: float
    gross_margin_pct: float
    competitor_count_radius: int
    confidence_score: float
    data_weight: float
    methodology_notes: dict = field(default_factory=dict)


_UNCERTAINTY_FACTOR = Decimal("0.30")


def _data_confidence(sample_size: int) -> float:
    """Tranzaksiya namuna hajmi asosida ma'lumotlar ishonchliligi (0.0–1.0)."""
    if sample_size >= 10_000:
        return 0.95
    if sample_size >= 1_000:
        return 0.80
    if sample_size >= 100:
        return 0.60
    if sample_size >= 10:
        return 0.40
    return 0.20


def _confidence_interval(value: Decimal, factor: Decimal) -> tuple[Decimal, Decimal]:
    delta = value * factor
    return max(Decimal(0), value - delta), value + delta


def run_market_sizing(data: MarketSizingInput) -> MarketSizingResult:
    """
    M-A1 asosiy hisoblash funksiyasi.

    Faqat sof matematik hisob — I/O yo'q, yon ta'sir yo'q.
    """
    # Bottom-up (benchmark asosida)
    tam_bottom_up = (
        Decimal(data.competitor_count_city) * data.avg_monthly_revenue_uzs * 12
    )
    sam_bottom_up = (
        Decimal(data.competitor_count_radius) * data.avg_monthly_revenue_uzs * 12
    )

    # Bayesian og'irlik: ma'lumotlar sifatiga qarab top-down ulushi
    w = Decimal(str(_data_confidence(data.transaction_sample_size)))
    w_inv = Decimal(1) - w

    # Bayesian birlashma
    tam = w * data.tam_transactions_uzs + w_inv * tam_bottom_up
    sam = w * data.sam_transactions_uzs + w_inv * sam_bottom_up

    # SOM = SAM × bozor ulushi × sifat koeffitsienti
    market_share = Decimal(1) / Decimal(data.competitor_count_radius + 1)
    som = sam * market_share * Decimal(str(data.quality_factor))

    # Ishonch oralig'i (±30%)
    tam_low, tam_high = _confidence_interval(tam, _UNCERTAINTY_FACTOR)
    sam_low, sam_high = _confidence_interval(sam, _UNCERTAINTY_FACTOR)
    som_low, som_high = _confidence_interval(som, _UNCERTAINTY_FACTOR)

    # Umumiy ishonch darajasi
    base_confidence = _data_confidence(data.transaction_sample_size)
    if data.competitor_count_city == 0:
        base_confidence *= 0.7
    if data.tam_transactions_uzs == 0:
        base_confidence *= 0.5

    return MarketSizingResult(
        tam_uzs=tam,
        sam_uzs=sam,
        som_uzs=som,
        tam_low_uzs=tam_low,
        tam_high_uzs=tam_high,
        sam_low_uzs=sam_low,
        sam_high_uzs=sam_high,
        som_low_uzs=som_low,
        som_high_uzs=som_high,
        market_share_pct=round(float(market_share) * 100, 2),
        market_growth_rate_pct=data.annual_growth_rate_pct,
        gross_margin_pct=data.gross_margin_pct,
        competitor_count_radius=data.competitor_count_radius,
        confidence_score=round(base_confidence, 3),
        data_weight=float(w),
        methodology_notes={
            "tam_bottom_up_uzs": float(tam_bottom_up),
            "tam_top_down_uzs": float(data.tam_transactions_uzs),
            "sam_bottom_up_uzs": float(sam_bottom_up),
            "sam_top_down_uzs": float(data.sam_transactions_uzs),
            "bayesian_weight_top_down": float(w),
            "market_share_formula": (
                f"1 / ({data.competitor_count_radius} + 1) × {data.quality_factor}"
            ),
        },
    )
