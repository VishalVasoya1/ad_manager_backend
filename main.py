"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config.postgres import init_db, close_db

from app.router.auth.auth import AuthRouter
from app.router.user.user import UserRouter
from app.router.application.application import ApplicationRouter
from app.router.ad_master.ad_master import AdMasterRouter
from app.router.ad_type.ad_type import AdTypeRouter
from app.router.ad_field.ad_field import AdFieldRouter


class AdManagerApp(FastAPI):
    """Main application class with CORS, routers, and lifecycle hooks."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._configure_cors()
        self._register_routers()
        self._register_lifecycle_events()

    def _configure_cors(self):
        """Allow all origins for development."""
        self.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    def _register_routers(self):
        """Mount all feature routers."""
        self.include_router(AuthRouter().router)
        self.include_router(UserRouter().router)
        self.include_router(ApplicationRouter().router)
        self.include_router(AdMasterRouter().router)
        self.include_router(AdTypeRouter().router)
        self.include_router(AdFieldRouter().router)

    async def _cleanup_blacklist_loop(self):
        """Periodically delete expired tokens from the blacklist every 10 minutes."""
        import asyncio
        from app.config.postgres import AsyncSessionLocal
        from app.model.token_blacklist import TokenBlacklist
        from app.config.settings import settings
        from sqlalchemy import delete
        from datetime import datetime, timedelta, timezone

        while True:
            try:
                expiry_threshold = datetime.now(timezone.utc) - timedelta(
                    minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
                )
                async with AsyncSessionLocal() as db:
                    await db.execute(
                        delete(TokenBlacklist).where(
                            TokenBlacklist.blacklisted_at < expiry_threshold
                        )
                    )
                    await db.commit()
            except Exception as e:
                print(f"⚠️ Blacklist cleanup error: {e}")
            await asyncio.sleep(600)

    def _register_lifecycle_events(self):
        """Register startup and shutdown handlers."""
        @self.on_event("startup")
        async def on_startup():
            print("🚀 Starting Ad Manager application...")
            await init_db()
            import asyncio
            asyncio.create_task(self._cleanup_blacklist_loop())
            print("✅ Application started")

        @self.on_event("shutdown")
        async def on_shutdown():
            print("🛑 Shutting down Ad Manager application...")
            await close_db()
            print("✅ Shutdown complete")


app = AdManagerApp(
    title="Ad Manager API",
    description="Ad Manager API for managing ads, applications, and users.",
    version="1.0.0",
    debug=True,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)


@app.get("/health", tags=["Health"])
async def health_check():
    """Return server health status."""
    return {"message": "Ad Manager API server is healthy."}


@app.get("/ping", tags=["Health"])
async def ping():
    """Basic connectivity check."""
    return {"message": "Welcome to Ad Manager API"}
