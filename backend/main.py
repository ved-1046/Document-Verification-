"""
DocuVerify AI — FastAPI Application Entry Point

Architecture decisions:
- All routes are versioned under /api/v1/
- CORS is configured from environment variables (never wildcard in production)
- The app never serves uploaded files directly; downloads go through an
  authorized endpoint that checks permissions before streaming.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1 import auth, documents, health, requests, reviews
from app.api.v1 import dashboard, assistant
from app.api.v1 import users

app = FastAPI(
    title="DocuVerify AI",
    description=(
        "AI-powered Document Verification and Approval System. "
        "Final decisions always belong to authorized humans."
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — origins come from environment, never hardcoded
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──────────────────────────────────────────────────────
app.include_router(health.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(requests.router, prefix="/api/v1")
app.include_router(documents.router, prefix="/api/v1")
app.include_router(reviews.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(assistant.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")


@app.get("/", include_in_schema=False)
def root():
    return {
        "name": "DocuVerify AI",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/api/v1/health",
    }
