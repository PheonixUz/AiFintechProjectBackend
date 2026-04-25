"""
M-A1 Market Sizing API route.

POST /api/v1/models/market-sizing
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.orchestrator import MarketSizingAgent
from app.api.deps import get_session
from app.schemas.request import MarketSizingRequest
from app.schemas.response import MarketSizingResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/models", tags=["M-A1: Market Sizing"])


@router.post(
    "/market-sizing",
    response_model=MarketSizingResponse,
    summary="M-A1 — Bozor hajmini hisoblash (TAM / SAM / SOM)",
    description=(
        "Berilgan biznes nishasi va GPS koordinatasi uchun TAM/SAM/SOM hisoblaydi. "
        "Bank tranzaksiyalari + sanoat benchmarklari asosida Bayesian + bottom-up."
    ),
)
async def market_sizing(
    body: MarketSizingRequest,
    session: AsyncSession = Depends(get_session),
) -> MarketSizingResponse:
    try:
        agent = MarketSizingAgent(session)
        return await agent.run(body)
    except RuntimeError as exc:
        logger.error("Agent xatosi: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Agent xatosi: {exc}",
        ) from exc
    except Exception as exc:
        logger.exception("Kutilmagan xato")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ichki server xatosi",
        ) from exc
