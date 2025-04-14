from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from fastapi import HTTPException
from contextvars import ContextVar
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from .database import AsyncSessionLocal, tenant_schema
from .models.public import Tenant
from .config import settings
import re
import logging

# Set up logging
logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
tenant_context = ContextVar("tenant_context", default=None)

class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        host = request.headers.get("host", "").split(":")[0]
        main_domain = settings.MAIN_DOMAIN
        request.state.is_public = False
        tenant = None

        if host in [main_domain, "localhost"]:
            request.state.is_public = True
        else:
            async with AsyncSessionLocal() as session:
                if host.endswith(f".{main_domain}"):
                    subdomain = host.replace(f".{main_domain}", "").split('.')[0]
                    print("hi",subdomain)
                    result = await session.execute(
                        select(Tenant).filter_by(subdomain=subdomain, is_active=True)
                    )
                else:
                    result = await session.execute(
                        select(Tenant).filter_by(custom_domain=host, is_active=True)
                    )
                tenant = result.scalars().first()

                if not tenant:
                    raise HTTPException(status_code=404, detail="Tenant not found")

                request.state.tenant = tenant
                tenant_schema.set(f"tenant_{tenant.id}")
                print(f"Middleware set tenant_schema to: {tenant_schema.get()}")  # Debugging print

                tenant_context.set(tenant.id)

        # async with AsyncSessionLocal() as test_session:
        #     result = await test_session.execute(text("SHOW search_path"))
        #     logger.debug(f"IMMEDIATE TEST search_path: {(await result.fetchone())[0]}")

        response = await call_next(request)
        return response