from decimal import Decimal

from pydantic import BaseModel, Field


class MarketSizingRequest(BaseModel):
    mcc_code: str = Field(
        ..., min_length=4, max_length=4, description="MCC kod (4 raqam)"
    )
    lat: float = Field(..., ge=-90, le=90, description="Kenglik (latitude)")
    lon: float = Field(..., ge=-180, le=180, description="Uzunlik (longitude)")
    radius_m: float = Field(
        default=1000, ge=100, le=10_000, description="Tahlil radiusi (metr)"
    )
    city: str = Field(default="Toshkent", description="Shahar nomi")
    capital_uzs: Decimal = Field(..., gt=0, description="Boshlang'ich kapital (UZS)")
    year: int = Field(default=2025, ge=2020, le=2030, description="Tahlil yili")
