from fastapi import APIRouter

from app.api.routes.churn_prediction import router as churn_prediction_router
from app.api.routes.data import router as data_router
from app.api.routes.demand_forecasting import router as demand_forecasting_router
from app.api.routes.market_sizing import router as market_sizing_router
from app.api.routes.viability_check import router as viability_check_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(market_sizing_router)
api_router.include_router(demand_forecasting_router)
api_router.include_router(viability_check_router)
api_router.include_router(churn_prediction_router)
api_router.include_router(data_router)
