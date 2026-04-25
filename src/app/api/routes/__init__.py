from fastapi import APIRouter

from app.api.routes.market_sizing import router as market_sizing_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(market_sizing_router)
