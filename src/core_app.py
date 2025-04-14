# core_app.py
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from fastapi.middleware import Middleware
from core.middleware import TenantMiddleware  # Import class-based middleware
from core.config import settings
from core.database import engine, PublicBase
from sqlalchemy import text
from core.models import *
from core.utils.setup import load_compliance_data, load_plans_data
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        # Ensure the "public" schema exists before running migrations
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS public"))
        
        # Set search path to public to avoid schema issues
        await conn.execute(text("SET search_path TO public"))
        
        # Create tables in the public schema
        await conn.run_sync(PublicBase.metadata.create_all)

        # Load initial data
        await load_compliance_data()
        await load_plans_data()

    yield
    await engine.dispose()

def create_app() -> FastAPI:
    app = FastAPI(
        # title=settings.APP_NAME,
        debug=settings.DEBUG,
        lifespan=lifespan,
        middleware=[Middleware(TenantMiddleware)]  # Pass class-based middleware here
    )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={"detail": exc.errors(), "body": exc.body},
        )

    # Security headers
    app.add_middleware(
        CORSMiddleware,
        # allow_origins=settings.CORS_ORIGINS,
        allow_origins=["http://mydummy.local:5173","http://tenant14.mydummy.local:5173", "http://localhost:5173", "https://4mz5jn92-5173.inc1.devtunnels.ms"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    return app
