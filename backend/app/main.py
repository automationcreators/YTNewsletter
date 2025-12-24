from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api.v1.router import api_router
from app.database import SessionLocal

app = FastAPI(
    title=settings.app_name,
    description="API for YouTube Newsletter Summarization SaaS",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "YouTube Newsletter API", "version": "0.1.0"}


@app.get("/health")
async def health_check():
    """Basic health check."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@app.get("/health/detailed")
async def detailed_health_check():
    """
    Detailed health check including database and Redis connectivity.

    Returns status of all critical services.
    """
    health = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {},
    }

    # Check database
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        health["services"]["database"] = {"status": "healthy"}
    except Exception as e:
        health["services"]["database"] = {"status": "unhealthy", "error": str(e)}
        health["status"] = "degraded"

    # Check Redis
    try:
        import redis
        r = redis.from_url(settings.redis_url)
        r.ping()
        health["services"]["redis"] = {"status": "healthy"}
    except Exception as e:
        health["services"]["redis"] = {"status": "unhealthy", "error": str(e)}
        health["status"] = "degraded"

    # Check Celery (optional - may not be running locally)
    try:
        from app.celery_app import celery_app
        inspect = celery_app.control.inspect()
        active = inspect.active()
        if active is not None:
            worker_count = len(active)
            health["services"]["celery"] = {
                "status": "healthy",
                "workers": worker_count,
            }
        else:
            health["services"]["celery"] = {
                "status": "no_workers",
                "message": "No Celery workers detected",
            }
    except Exception as e:
        health["services"]["celery"] = {
            "status": "unavailable",
            "error": str(e),
        }

    return health


# Include API v1 routes
app.include_router(api_router, prefix="/api/v1")
