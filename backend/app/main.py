import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.database import Base, engine
from app.routes import admin, auth, monitoring, sites, sso

settings = get_settings()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Setup Azure Application Insights if configured
if settings.APPINSIGHTS_CONNECTION_STRING:
    try:
        from opencensus.ext.azure.log_exporter import AzureLogHandler

        logger.addHandler(
            AzureLogHandler(
                connection_string=settings.APPINSIGHTS_CONNECTION_STRING
            )
        )
    except Exception as e:
        logger.warning(f"Could not configure Application Insights: {e}")

app = FastAPI(
    title=settings.APP_NAME,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(sites.router, prefix=settings.API_V1_PREFIX)
app.include_router(monitoring.router, prefix=settings.API_V1_PREFIX)
app.include_router(admin.router, prefix=settings.API_V1_PREFIX)
app.include_router(sso.router, prefix=settings.API_V1_PREFIX)


@app.on_event("startup")
async def startup():
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)

    # Ensure at least one admin user exists
    from app.core.database import SessionLocal
    from app.models.models import User
    db = SessionLocal()
    try:
        admin_count = db.query(User).filter(User.is_admin == True).count()
        if admin_count == 0:
            first_user = db.query(User).order_by(User.id).first()
            if first_user:
                first_user.is_admin = True
                db.commit()
                logger.info(f"Promoted '{first_user.email}' to admin (no admin existed)")
    finally:
        db.close()

    from app.services.scheduler_service import start_scheduler
    start_scheduler()

    logger.info("Application started with background scheduler")


@app.on_event("shutdown")
async def shutdown():
    from app.services.scheduler_service import stop_scheduler
    stop_scheduler()


@app.get("/health")
def health():
    return {"status": "healthy"}
