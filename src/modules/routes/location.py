# app/routers/clinic.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from core.models.tenant import Clinic, Location, User
from core.dependencies import get_current_admin, get_current_user, get_db
from modules.pydantic_model.location import LocationCreate, LocationUpdate, LocationResponse      


router = APIRouter(prefix="/location", tags=["location"])


# Location Endpoints (nested under clinics)
@router.post("/{clinic_id}/locations", response_model=LocationResponse, status_code=201)
async def create_location(
    clinic_id: int,
    location: LocationCreate,
    db: AsyncSession = Depends(get_db),
):
    clinic = await db.get(Clinic, clinic_id)
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")
    
    db_location = Location(**location.dict(), clinic_id=clinic_id)
    db.add(db_location)
    await db.commit()
    await db.refresh(db_location)
    return db_location

@router.get("/{clinic_id}/locations", response_model=list[LocationResponse])
async def read_clinic_locations(
    clinic_id: int,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    clinic = await db.get(Clinic, clinic_id)
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")
    
    result = await db.execute(
        select(Location)
        .where(Location.clinic_id == clinic_id)
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()

@router.get("/{clinic_id}/locations/{location_id}", response_model=LocationResponse)
async def read_location(
    clinic_id: int,
    location_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    clinic = await db.get(Clinic, clinic_id)
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")
    
    location = await db.get(Location, location_id)
    if not location or location.clinic_id != clinic_id:
        raise HTTPException(status_code=404, detail="Location not found")
    
    return location

@router.put("/{clinic_id}/locations/{location_id}", response_model=LocationResponse)
async def update_location(
    clinic_id: int,
    location_id: int,
    location_data: LocationUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_admin)  # Only admin can update locations
):
    clinic = await db.get(Clinic, clinic_id)
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")
    
    location = await db.get(Location, location_id)
    if not location or location.clinic_id != clinic_id:
        raise HTTPException(status_code=404, detail="Location not found")
    
    for field, value in location_data.dict(exclude_unset=True).items():
        setattr(location, field, value)
    
    await db.commit()
    await db.refresh(location)
    return location

@router.delete("/{clinic_id}/locations/{location_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_location(
    clinic_id: int,
    location_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_admin)  # Only admin can delete locations
):
    clinic = await db.get(Clinic, clinic_id)
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")
    
    location = await db.get(Location, location_id)
    if not location or location.clinic_id != clinic_id:
        raise HTTPException(status_code=404, detail="Location not found")
    
    await db.delete(location)
    await db.commit()
    return None