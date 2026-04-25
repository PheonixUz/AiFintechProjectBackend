"""
MCC kategoriyalari va bank tranzaksiyalari.

M-A1 Market Sizing uchun asosiy ma'lumot manbai:
  - TAM: shahar bo'yicha MCC kategoriyasidagi barcha tranzaksiyalar yig'indisi
  - SAM: berilgan radius ichidagi tranzaksiyalar yig'indisi
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base


class MCCCategory(Base):
    """MCC kod kataloği — bank tranzaksiyalarini nishaga moslashtirish uchun."""

    __tablename__ = "mcc_categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    mcc_code: Mapped[str] = mapped_column(String(4), unique=True, nullable=False)
    category_name_en: Mapped[str] = mapped_column(String(100), nullable=False)
    niche_name_uz: Mapped[str] = mapped_column(String(100), nullable=False)
    niche_name_ru: Mapped[str] = mapped_column(String(100), nullable=False)
    # e.g., "Oziq-ovqat", "Kiyim-kechak", "Sog'liqni saqlash"
    parent_category: Mapped[str] = mapped_column(String(50), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    transactions: Mapped[list["Transaction"]] = relationship(back_populates="mcc_category")

    def __repr__(self) -> str:
        return f"<MCCCategory {self.mcc_code}: {self.niche_name_uz}>"


class Transaction(Base):
    """
    Anonymlashtirilgan bank karta tranzaksiyalari.

    Har bir yozuv — bir karta to'lovi.
    Merchant (do'kon/xizmat) joylashuvi bo'yicha TAM/SAM hisoblash uchun ishlatiladi.
    """

    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False)
    amount_uzs: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    mcc_code: Mapped[str] = mapped_column(
        String(4), ForeignKey("mcc_categories.mcc_code"), nullable=False
    )

    # Merchant joylashuvi (do'kon/restoran/xizmat nuqtasi)
    merchant_lat: Mapped[float | None] = mapped_column(nullable=True)
    merchant_lon: Mapped[float | None] = mapped_column(nullable=True)
    merchant_district: Mapped[str | None] = mapped_column(String(100), nullable=True)
    merchant_city: Mapped[str] = mapped_column(String(100), nullable=False, default="Toshkent")

    # Anonymlashtirilgan mijoz ma'lumotlari (segmentatsiya uchun)
    customer_age_group: Mapped[str | None] = mapped_column(
        String(10), nullable=True
    )  # "18-25", "26-35", "36-50", "50+"
    customer_gender: Mapped[str | None] = mapped_column(String(1), nullable=True)  # "M", "F"

    is_online: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    mcc_category: Mapped["MCCCategory"] = relationship(back_populates="transactions")

    __table_args__ = (
        # TAM so'rovlari: shahar + MCC + sana oralig'i
        Index("ix_transactions_city_mcc_date", "merchant_city", "mcc_code", "transaction_date"),
        # SAM so'rovlari: koordinata bo'yicha bounding box filter
        Index("ix_transactions_lat_lon", "merchant_lat", "merchant_lon"),
        Index("ix_transactions_mcc_date", "mcc_code", "transaction_date"),
    )

    def __repr__(self) -> str:
        return f"<Transaction {self.id}: {self.mcc_code} {self.amount_uzs} UZS>"
