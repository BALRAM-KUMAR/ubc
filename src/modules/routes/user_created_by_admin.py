from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from core.models.tenant import User, Role, Department, Location, Provider, Patient
from sqlalchemy import select, case, or_, func
from core.dependencies import get_db, get_current_admin
from ..pydantic_model.user import UserCreate, UserResponse
from core.security import get_password_hash
from sqlalchemy.exc import SQLAlchemyError


from typing import List, Optional
from fastapi import Query
from sqlalchemy.orm import aliased
from pydantic import BaseModel

class UserListResponse(BaseModel):
    id: int
    email: str
    role: str
    department: str
    username: Optional[str]= None

    location: str
    is_provider: bool
    is_patient: bool

router = APIRouter(prefix="/users", tags=["users"])

@router.post("/create", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    try:
        # Validate role
        role = await db.get(Role, user_data.role_id)
        if not role:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

        # Validate department
        department = await db.get(Department, user_data.department_id)
        if not department:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")

        # Validate location
        location = await db.get(Location, user_data.location_id)
        if not location:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location not found")

        # Check for duplicate email
        result = await db.execute(select(User).where(User.email == user_data.email))
        if result.scalars().first():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

        # Create user and provider in one transaction
        new_user = User(
            email=user_data.email,
            password_hash=get_password_hash(user_data.password),
            role_id=user_data.role_id,
            tenant_id=admin.tenant_id
        )
        db.add(new_user)
        await db.flush()  # Get new_user.id before commit

        new_provider = Provider(
            user_id=new_user.id,
            department_id=user_data.department_id,
            location_id=user_data.location_id,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            phone_number=user_data.phone_number,
            dob=user_data.dob,
            gender=user_data.gender,
            license_number=user_data.license_number,
            specialty=user_data.specialty,
            qualifications=user_data.qualifications,
            availability=user_data.availability
        )
        db.add(new_provider)

        await db.commit()  # Only commit if both are added
        await db.refresh(new_user)
        return new_user

    except HTTPException:
        raise  # re-raise known HTTP errors

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


@router.get("/user-list", response_model=List[UserListResponse], status_code=status.HTTP_200_OK)
async def get_users(
    role_name: Optional[str] = Query(None, description="Filter by role name"),
    department_id: Optional[int] = Query(None, description="Filter by department ID"),
    location_id: Optional[int] = Query(None, description="Filter by location ID"),
    is_provider: Optional[bool] = Query(None, description="Filter by provider status"),
    is_patient: Optional[bool] = Query(None, description="Filter by patient status"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_admin)
):
    # Create aliases for joined tables
    ProviderDepartment = aliased(Department)
    ProviderLocation = aliased(Location)
    PatientDepartment = aliased(Department)
    PatientLocation = aliased(Location)

    # Base query
    query = (
        select(
            User.id,
            User.email,
            User.username,
            Role.name.label("role_name"),
            func.coalesce(
                ProviderDepartment.name, 
                PatientDepartment.name, 
                'NF'
            ).label("department"),
            func.coalesce(
                ProviderLocation.name,
                PatientLocation.name,
                'NF'
            ).label("location"),
            Provider.id.isnot(None).label("is_provider"),
            Patient.id.isnot(None).label("is_patient")
        )
        .select_from(User)
        .join(Role, User.role_id == Role.id)
        .outerjoin(Provider, User.id == Provider.user_id)
        .outerjoin(Patient, User.id == Patient.user_id)
        .outerjoin(ProviderDepartment, Provider.department_id == ProviderDepartment.id)
        .outerjoin(ProviderLocation, Provider.location_id == ProviderLocation.id)
        .outerjoin(PatientDepartment, Patient.department_id == PatientDepartment.id)
        .outerjoin(PatientLocation, Patient.location_id == PatientLocation.id)
    )

    # Apply filters
    if role_name:
        query = query.where(Role.name == role_name)
        
    if department_id:
        query = query.where(or_(
            ProviderDepartment.id == department_id,
            PatientDepartment.id == department_id
        ))
        
    if location_id:
        query = query.where(or_(
            ProviderLocation.id == location_id,
            PatientLocation.id == location_id
        ))
        
    if is_provider is not None:
        query = query.where(Provider.id.isnot(None) if is_provider else query.where(Provider.id.is_(None)))
        
    if is_patient is not None:
        query = query.where(Patient.id.isnot(None) if is_patient else query.where(Patient.id.is_(None)))

    result = await db.execute(query)
    users = result.all()

    return [
        UserListResponse(
            id=row.id,
            username = row.username if row.username else 'NF',
            email=row.email,
            role=row.role_name,
            department=row.department,
            location=row.location,
            is_provider=row.is_provider,
            is_patient=row.is_patient
        ) for row in users
    ]

# import secrets
# from fastapi import BackgroundTasks
# from core.utils.email import send_invitation_email

# @router.post("/invite", response_model=dict, status_code=status.HTTP_201_CREATED)
# async def invite_user(
#     email: str,
#     db: AsyncSession = Depends(get_db),
#     admin: User = Depends(get_current_admin),
#     background_tasks: BackgroundTasks = BackgroundTasks()
# ):
#     # Check if email is already registered
#     existing_user = await db.execute(select(User).where(User.email == email))
#     if existing_user.scalars().first():
#         raise HTTPException(status_code=400, detail="Email already registered")

#     # Generate invitation token
#     invitation_token = secrets.token_urlsafe(32)

#     # Save the invitation in the database
#     new_user = User(
#         email=email,
#         invitation_token=invitation_token,
#         invitation_status="pending",
#         tenant_id=admin.tenant_id
#     )
#     db.add(new_user)
#     await db.commit()
#     await db.refresh(new_user)

#     # Send invitation email asynchronously
#     background_tasks.add_task(
#         send_invitation_email,
#         recipient_email=email,
#         invitation_token=invitation_token
#     )

#     return {"message": "Invitation sent successfully"}


from fastapi import Form

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    token: str = Form(...),
    password: str = Form(...),
    first_name: str = Form(...),
    last_name: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    # Find the user by invitation token
    user = await db.execute(select(User).where(User.invitation_token == token))
    user = user.scalars().first()

    if not user or user.invitation_status != "pending":
        raise HTTPException(status_code=400, detail="Invalid or expired invitation token")

    # Update user details
    user.password_hash = password  # Ensure this is hashed before storage
    user.first_name = first_name
    user.last_name = last_name
    user.invitation_status = "completed"

    await db.commit()
    await db.refresh(user)

    return user