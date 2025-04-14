from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import select

from core.models.tenant import User, Role
from core.dependencies import get_db, get_current_user, get_current_admin

from pydantic import BaseModel
from typing import Optional, List


from sqlalchemy import func

router = APIRouter(prefix="/roles", tags=["roles"])

class RoleCreate(BaseModel):
    name: str
    permissions: Optional[dict] = {}
    is_custom: Optional[bool] = True

class RoleOut(BaseModel):
    id: int
    name: str
    permissions: Optional[dict]
    is_custom: bool

    class Config:
        orm_mode = True


@router.get("/", response_model=List[RoleOut], status_code=status.HTTP_200_OK)
async def get_roles(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    try:
        query = select(Role)
        result = await db.execute(query)
        roles = result.scalars().all()

        return roles
    
    except HTTPException as e:
        raise e

    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}"
        )


@router.post("/", response_model=RoleOut, status_code=status.HTTP_201_CREATED)
async def create_role(
    role_data: RoleCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):


    try:

        query = select(Role).where(func.lower(Role.name) == role_data.name.lower())
        result = await db.execute(query)
        role = result.scalars().first()

        if role:
            raise HTTPException(status_code=400, detail="Role already exist")

        new_role = Role(
            name=role_data.name,
            permissions=role_data.permissions,
            is_custom=role_data.is_custom
        )
        db.add(new_role)
        await db.commit()
        await db.refresh(new_role)
        return new_role

    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )


@router.get("/{role_id}", response_model=RoleOut, status_code=status.HTTP_200_OK)
async def get_role_by_id(
    role_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    try:
        query = select(Role).where(Role.id == role_id)
        result = await db.execute(query)
        role = result.scalar_one_or_none()

        if not role:
            raise HTTPException(status_code=404, detail="Role not found")

        return role

    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )
