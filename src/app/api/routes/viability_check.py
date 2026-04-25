"""
M-D1 Financial Viability Check API route.

POST /api/v1/models/viability-check
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.viability_check import ViabilityCheckAgent
from app.api.deps import get_session
from app.schemas.request import ViabilityCheckRequest
from app.schemas.response import ViabilityCheckResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/models", tags=["M-D1: Financial Viability"])


@router.post(
    "/viability-check",
    response_model=ViabilityCheckResponse,
    summary="M-D1 - Biznes-plan moliyaviy yashovchanligini tekshirish",
    description=(
        "Biznes-plan uchun break-even, runway, 24 oylik survival probability "
        "va Monte Carlo cashflow risklarini hisoblaydi."
    ),
)
async def viability_check(
    body: ViabilityCheckRequest,
    session: AsyncSession = Depends(get_session),
) -> ViabilityCheckResponse:
    try:
        agent = ViabilityCheckAgent(session)
        return await agent.run(body)
    except RuntimeError as exc:
        logger.error("Viability Check agent xatosi: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        logger.error("Viability Check validatsiya xatosi: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("Kutilmagan xato")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ichki server xatosi",
        ) from exc
