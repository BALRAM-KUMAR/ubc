from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from core.dependencies import get_db, get_tenant_user, get_current_admin
from core.models.tenant import User, Role
from sqlalchemy import select
from modules.pydantic_model.auth_schemas import UserCreate, UserResponse, UserLogin, Token
from core.security import get_password_hash, verify_password, create_access_token
from core.dependencies import get_current_user
import json

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Updated signup endpoint and token handling
@router.post("/signup", response_model=Token)
async def signup(
    request: Request,
    user_data: UserCreate, 
    db: AsyncSession = Depends(get_db) 
):
    tenant = getattr(request.state, "tenant", None)

    print("tenant",tenant)
    
    # Check if user exists
    query = select(User).where(User.email == user_data.email)
    if tenant:
        query = query.where(User.tenant_id == tenant.id)
    else:
        query = query.where(User.tenant_id.is_(None))

    existing_user = await db.execute(query)
    if existing_user.scalars().first():
        raise HTTPException(400, "Email already registered in this context")

    # Fetch role
    role_query = select(Role).where(Role.name == 'patient')
    role = (await db.execute(role_query)).scalars().first()

    if not role:
        raise HTTPException(400, "Role 'patient' not found")


    new_user = User(
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        tenant_id=tenant.id if tenant else None,
        role_id=role.id,
        is_active=True
    )

    try:
        db.add(new_user)
        await db.commit()  # Commit if no error occurs
        await db.refresh(new_user)
    except IntegrityError:
        await db.rollback()  # Rollback to clean up the session
        raise HTTPException(400, "Email already exists in this tenant context")

    token_data = {
        "sub": str(new_user.id),
        "tenant_id": str(new_user.tenant_id) if new_user.tenant_id else "public"
    }

    return {
        "access_token": create_access_token(token_data),
        "token_type": "bearer"
    }

# Updated login endpoint
@router.post("/login", response_model=Token)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    tenant = getattr(request.state, "tenant", None)
    
    # Construct query with proper schema context
    query = select(User).filter_by(email=form_data.username)
    
    if tenant:
        query = query.where(User.tenant_id == tenant.id)
    else:
        query = query.where(User.tenant_id.is_(None))
    
    try:
        result = await db.execute(query)
        user = result.scalars().first()
        
        if not user or not verify_password(form_data.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
            
        access_token = create_access_token(
            data={
                "sub": str(user.id),
                "tenant_id": str(user.tenant_id) if user.tenant_id else "public"
            }
        )
        
        return {"access_token": access_token, "token_type": "bearer"}
        
    except Exception as e:
        print(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )
    
@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_tenant_user)):
    return user


#sample route with dependencies
# class UserResponse(BaseModel):
#     id: int
#     tenant_id: int
#     role_id: int
#     email: EmailStr
#     is_active: bool
#     last_login: Optional[datetime] = None
#     created_at: datetime
# **session is begin you have to hnadle rollback**
# @router.get("/anyendpoint", response_model=UserResponse)
# async def get_me(db: AsyncSession = Depends(get_db), user: User = Depends(get_tenant_user)):
#     return user

@router.get("/tenant/settings")
async def get_tenant_settings(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    if not hasattr(request.state, "tenant"):
        raise HTTPException(404, "Tenant not found")
    
    return {
        "logo": request.state.tenant.settings.get("logo"),
        "primaryColor": request.state.tenant.settings.get("primary_color", "#2563eb"),
        "clinicName": request.state.tenant.name
    }


################################for testing only###############
#Public Route (mylocal.dummy)
@router.get("/public-data")
async def public_data(user: User = Depends(get_current_user)):
    # Accessible to any authenticated user
    return {"message": f"Public data{user.tenant_id}"}

#Tenant-Specific Route (tenant1.mylocal.dummy)
@router.get("/tenant-data")
async def tenant_data(user: User = Depends(get_tenant_user)):
    # Only accessible to tenant-associated users
    return {"message": f"Data for tenant {user.tenant_id}"}



@router.get("/admin")
async def admin_panel(user: User = Depends(get_current_admin)):
    return {"message": user}