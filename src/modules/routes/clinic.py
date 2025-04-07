# app/routers/clinic.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from core.models.tenant import Clinic, Location, Department, User
from core.dependencies import get_current_admin, get_current_user, get_db
from modules.pydantic_model.clinic import ClinicCreate, ClinicResponse

router = APIRouter(prefix="/clinics", tags=["clinics"])

# Clinic Endpoints
@router.post("/", response_model=ClinicResponse, status_code=status.HTTP_201_CREATED)
async def create_clinic(
    clinic: ClinicCreate,
    db: AsyncSession = Depends(get_db),
):
    db_clinic = Clinic(**clinic.dict())
    db.add(db_clinic)
    await db.commit()
    await db.refresh(db_clinic)
    return db_clinic

@router.get("/", response_model=list[ClinicResponse])
async def read_clinics(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    result = await db.execute(select(Clinic).offset(skip).limit(limit))
    return result.scalars().all()

@router.get("/{clinic_id}", response_model=ClinicResponse)
async def read_clinic(
    clinic_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    clinic = await db.get(Clinic, clinic_id)
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")
    return clinic

@router.put("/{clinic_id}", response_model=ClinicResponse)
async def update_clinic(
    clinic_id: int,
    clinic: ClinicCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_admin)
):
    db_clinic = await db.get(Clinic, clinic_id)
    if not db_clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")
    
    for key, value in clinic.dict().items():
        setattr(db_clinic, key, value)
    
    await db.commit()
    await db.refresh(db_clinic)
    return db_clinic

@router.delete("/{clinic_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_clinic(
    clinic_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_admin)
):
    db_clinic = await db.get(Clinic, clinic_id)
    if not db_clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")
    
    await db.delete(db_clinic)
    await db.commit()

