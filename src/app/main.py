import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import api_router
from app.config import settings

logging.basicConfig(level=settings.log_level)

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="KMB AI Business Analysis Platform — M-A1 Market Sizing",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health", tags=["system"])
async def health() -> dict:
    return {"status": "ok", "version": settings.app_version}
