from pydantic import BaseModel, EmailStr
from typing import Optional

class ProviderCreate(BaseModel):
    department_id: int
    location_id: int
    first_name: str
    last_name: str
    specialty: str

class UserCreate(BaseModel):
    email: EmailStr
    role_id: int
    provider_data: Optional[ProviderCreate] = None



from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from core.dependencies import get_db, get_current_admin, get_tenant_user
from core.models.tenant import User, Role, Provider, Department, Location
# from ..schemas import UserCreate
import secrets
from passlib.context import CryptContext

router = APIRouter(
    prefix="/userbyadmin",
    tags=["userbyadmin"],
    dependencies=[Depends(get_tenant_user)]

)



pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def generate_random_password(length=12):
    return secrets.token_urlsafe(length)

@router.post("/users")
async def create_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    # Check role exists
    role = await db.get(Role, user_data.role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    # Check email uniqueness within tenant
    existing_user = await db.execute(
        select(User).where(
            User.email == user_data.email,
            User.tenant_id == admin.tenant_id
        )
    )
    if existing_user.scalars().first():
        raise HTTPException(status_code=400, detail="Email already exists")

    # Generate password
    password = generate_random_password()
    hashed_password = pwd_context.hash(password)

    # Create user
    user = User(
        email=user_data.email,
        password_hash=hashed_password,
        role_id=user_data.role_id,
        tenant_id=admin.tenant_id,
        is_active=True
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Create Provider if role requires
    if role.name in ["staff", "provider"]:
        if not user_data.provider_data:
            raise HTTPException(
                status_code=400,
                detail="Provider data required for this role"
            )

        # Validate department and location belong to tenant
        department = await db.execute(
            select(Department)
            .join(Location)
            .filter(
                Department.id == user_data.provider_data.department_id,
                Location.tenant_id == admin.tenant_id
            )
        )
        department = department.scalars().first()

        location = await db.get(Location, user_data.provider_data.location_id)
        if not department or not location or location.tenant_id != admin.tenant_id:
            raise HTTPException(status_code=404, detail="Invalid department or location")

        # Create Provider
        provider = Provider(
            user_id=user.id,
            department_id=user_data.provider_data.department_id,
            location_id=user_data.provider_data.location_id,
            first_name=user_data.provider_data.first_name,
            last_name=user_data.provider_data.last_name,
            specialty=user_data.provider_data.specialty
        )
        db.add(provider)
        await db.commit()

    # Send email (pseudo-code)
    # send_email(admin.email, f"New user created. Password: {password}")

    return {"email": user.email, "password": password}  # Return for testing