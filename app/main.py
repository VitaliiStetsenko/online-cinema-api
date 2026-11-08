"""Main FastAPI application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIASGIMiddleware
from slowapi import _rate_limit_exceeded_handler
from app.core.config import settings
from app.api.auth import router as auth_router
from app.api.cart import router as cart_router
from app.api.favorites import router as favorites_router
from app.api.interactions import router as interactions_router
from app.api.movies import catalog_router, router as movies_router
from app.api.users import router as users_router
from app.core.rate_limit import limiter

app = FastAPI(
    title=settings.app_title,
    version=settings.app_version,
    debug=settings.debug,
    docs_url="/docs",
    redoc_url=None,
    openapi_url="/openapi.json",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIASGIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api")
app.include_router(cart_router, prefix="/api")
app.include_router(favorites_router, prefix="/api")
app.include_router(interactions_router, prefix="/api")
app.include_router(users_router, prefix="/api")
app.include_router(movies_router, prefix="/api")
app.include_router(catalog_router, prefix="/api")


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "message": "Online Cinema API"}
