from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import text
from typing import AsyncGenerator
from .database import AsyncSessionLocal, tenant_schema
from .config import settings
from .models.tenant import User, Role

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_PREFIX}/auth/login")

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        current_schema = tenant_schema.get()
        await session.execute(text(f"SET search_path TO {current_schema}"))
        try:
            yield session
        finally:
            await session.close()

async def get_current_user(
    request: Request,
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
        user_id_str = payload.get("sub")
        token_tenant_id = payload.get("tenant_id")
        
        if not user_id_str or not token_tenant_id:
            raise credentials_exception
            
        user_id = int(user_id_str)
    except (JWTError, ValueError):
        raise credentials_exception

    # Build tenant-aware query
    query = select(User).where(User.id == user_id)
    
    if token_tenant_id == "public":
        query = query.where(User.tenant_id.is_(None))
    else:
        try:
            query = query.where(User.tenant_id == int(token_tenant_id))
        except ValueError:
            raise credentials_exception

    result = await db.execute(query)
    user = result.scalars().first()

    if not user:
        raise credentials_exception

    # Additional security check
    if (token_tenant_id == "public" and user.tenant_id is not None) or \
       (token_tenant_id != "public" and user.tenant_id != int(token_tenant_id)):
        raise credentials_exception

    request.state.user = user
    return user

async def get_tenant_user(
    request: Request,
    user: User = Depends(get_current_user)
) -> User:
    if not hasattr(request.state, "tenant"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant context required"
        )
        
    if user.tenant_id != request.state.tenant.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied for tenant"
        )
    
    return user

async def get_current_admin(user: User = Depends(get_current_user),
                        db: AsyncSession = Depends(get_db)
):
    query = select(Role).where(Role.id==user.role_id)
    result = await db.execute(query)
    role = result.scalars().first()
    if role.name != "clinic_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return user


async def get_medical_context(
    request: Request,
    user: User = Depends(get_current_user)
):
    if user.role not in ["doctor", "nurse", "admin"]:
        raise HTTPException(403, "Medical staff access required")
    return user

def public_route_required(request: Request):
    if not getattr(request.state, "is_public", False):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Public route not found"
        )

def tenant_route_required(request: Request):
    if not hasattr(request.state, "tenant"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant route not found"
        )