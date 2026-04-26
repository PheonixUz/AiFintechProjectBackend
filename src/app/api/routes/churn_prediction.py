"""
M-E2 Churn Prediction API route.

POST /api/v1/models/churn-prediction
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.churn_prediction import ChurnPredictionAgent
from app.api.deps import get_session
from app.schemas.request import ChurnPredictionRequest
from app.schemas.response import ChurnPredictionResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/models", tags=["M-E2: Churn Prediction"])


@router.post(
    "/churn-prediction",
    response_model=ChurnPredictionResponse,
    summary="M-E2 - Biznes yopilish ehtimolini bashorat qilish",
    description=(
        "SMB biznesining birinchi 2 yil ichida yopilish ehtimolini "
        "hisoblaydi va top-3 risk faktorini qaytaradi."
    ),
)
async def churn_prediction(
    body: ChurnPredictionRequest,
    session: AsyncSession = Depends(get_session),
) -> ChurnPredictionResponse:
    try:
        agent = ChurnPredictionAgent(session)
        return await agent.run(body)
    except RuntimeError as exc:
        logger.error("Churn Prediction agent xatosi: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        logger.error("Churn Prediction validatsiya xatosi: %s", exc)
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
