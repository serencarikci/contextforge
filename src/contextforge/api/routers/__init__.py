"""API routers."""

from fastapi import APIRouter

from contextforge.api.routers import (
    audit,
    customers,
    documents,
    health,
    knowledge_spaces,
    memberships,
    organizations,
    projects,
    roles,
    system,
    users,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(system.router, tags=["system"])
api_router.include_router(organizations.router)
api_router.include_router(users.router)
api_router.include_router(memberships.router)
api_router.include_router(roles.router)
api_router.include_router(customers.router)
api_router.include_router(projects.router)
api_router.include_router(knowledge_spaces.router)
api_router.include_router(documents.router)
api_router.include_router(audit.router)
