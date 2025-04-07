# app/routers/department.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from core.models.tenant import Department, Clinic, Location, User
from core.dependencies import get_current_admin, get_current_user, get_db
from modules.pydantic_model.department import DepartmentCreate, DepartmentResponse

router = APIRouter(prefix="/clinics/{clinic_id}/locations/{location_id}/departments", tags=["departments"])

@router.post("/", response_model=DepartmentResponse, status_code=201)
async def create_department(
    clinic_id: int,
    location_id: int,
    department: DepartmentCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_admin)
):
    # Verify clinic exists
    clinic = await db.get(Clinic, clinic_id)
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")
    
    # Verify location exists and belongs to clinic
    location = await db.get(Location, location_id)
    if not location or location.clinic_id != clinic_id:
        raise HTTPException(status_code=404, detail="Location not found in clinic")
    
    db_department = Department(**department.dict(), clinic_id=clinic_id, location_id=location_id)
    db.add(db_department)
    await db.commit()
    await db.refresh(db_department)
    return db_department

@router.get("/", response_model=list[DepartmentResponse])
async def read_location_departments(
    clinic_id: int,
    location_id: int,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    # Verify clinic and location
    clinic = await db.get(Clinic, clinic_id)
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")
    
    location = await db.get(Location, location_id)
    if not location or location.clinic_id != clinic_id:
        raise HTTPException(status_code=404, detail="Location not found in clinic")
    
    result = await db.execute(
        select(Department)
        .where(Department.location_id == location_id)
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()

# Individual department operations
@router.get("/{department_id}", response_model=DepartmentResponse)
async def read_department(
    department_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    department = await db.get(Department, department_id)
    if not department:
        raise HTTPException(status_code=404, detail="Department not found")
    return department

@router.put("/{department_id}", response_model=DepartmentResponse)
async def update_department(
    department_id: int,
    department: DepartmentCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_admin)
):
    db_department = await db.get(Department, department_id)
    if not db_department:
        raise HTTPException(status_code=404, detail="Department not found")
    
    for key, value in department.dict().items():
        setattr(db_department, key, value)
    
    await db.commit()
    await db.refresh(db_department)
    return db_department

@router.delete("/{department_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_department(
    department_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_admin)
):
    department = await db.get(Department, department_id)
    if not department:
        raise HTTPException(status_code=404, detail="Department not found")
    
    await db.delete(department)
    await db.commit()