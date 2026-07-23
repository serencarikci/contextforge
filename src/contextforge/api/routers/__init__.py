"""API routers."""

from fastapi import APIRouter

from contextforge.api.routers import health, system

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(system.router, tags=["system"])
