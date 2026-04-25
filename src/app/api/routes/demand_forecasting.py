"""
M-B1 Demand Forecasting API route.

POST /api/v1/models/demand-forecast
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.demand_forecasting import DemandForecastAgent
from app.api.deps import get_session
from app.schemas.request import DemandForecastRequest
from app.schemas.response import DemandForecastResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/models", tags=["M-B1: Demand Forecasting"])


@router.post(
    "/demand-forecast",
    response_model=DemandForecastResponse,
    summary="M-B1 - Nisha revenue prognozi",
    description=(
        "Berilgan nisha va shahar uchun 12/24/36 oylik revenue forecast "
        "hisoblaydi. Natijada ishonch intervali bilan oyma-oy prognoz qaytadi."
    ),
)
async def demand_forecast(
    body: DemandForecastRequest,
    session: AsyncSession = Depends(get_session),
) -> DemandForecastResponse:
    try:
        if body.horizon_months not in (12, 24, 36):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="horizon_months faqat 12, 24 yoki 36 bo'lishi mumkin",
            )
        agent = DemandForecastAgent(session)
        return await agent.run(body)
    except HTTPException:
        raise
    except RuntimeError as exc:
        logger.error("Demand forecast agent xatosi: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("Kutilmagan xato")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ichki server xatosi",
        ) from exc
