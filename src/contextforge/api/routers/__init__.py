from fastapi import APIRouter

from contextforge.api.routers import (
    admin,
    audit,
    chat_analytics,
    conversations,
    customers,
    documents,
    health,
    ingestion_jobs,
    knowledge_spaces,
    memberships,
    messages,
    organizations,
    projects,
    rag,
    roles,
    system,
    users,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(system.router, tags=["system"])
api_router.include_router(admin.router)
api_router.include_router(organizations.router)
api_router.include_router(users.router)
api_router.include_router(memberships.router)
api_router.include_router(roles.router)
api_router.include_router(customers.router)
api_router.include_router(projects.router)
api_router.include_router(knowledge_spaces.router)
api_router.include_router(documents.router)
api_router.include_router(ingestion_jobs.router)
api_router.include_router(ingestion_jobs.documents_ingestion_router)
api_router.include_router(rag.router)
api_router.include_router(conversations.router)
api_router.include_router(messages.router)
api_router.include_router(chat_analytics.router)
api_router.include_router(audit.router)
