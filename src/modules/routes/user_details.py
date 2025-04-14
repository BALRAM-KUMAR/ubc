from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.future import select
from core.dependencies import get_db, get_current_admin
from core.models.tenant import User, Provider, Patient, Department, Location, Clinic
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

router = APIRouter(prefix="/users", tags=["user_details"])

# Pydantic Models
class ProviderResponse(BaseModel):
    id: int
    first_name: str
    last_name: str
    phone_number: str
    dob: datetime
    gender: str
    license_number: str
    specialty: str
    qualifications: dict
    availability: dict
    department: Optional[str]
    location: Optional[str]
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class PatientResponse(BaseModel):
    id: int
    first_name: str
    last_name: str
    phone_number: str
    date_of_birth: datetime
    gender: str
    encrypted_ssn: str
    insurance_provider: str
    policy_number: str
    clinic: Optional[str]
    location: Optional[str]
    department: Optional[str]
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

# Endpoints
@router.get("/{user_id}/provider", response_model=ProviderResponse)
async def get_provider_by_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    result = await db.execute(
        select(Provider)
        .options(
            selectinload(Provider.department),
            selectinload(Provider.location)
        )
        .where(Provider.user_id == user_id)
    )
    provider = result.scalar()

    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not found for this user"
        )

    return {
        "id": provider.id,
        "first_name": provider.first_name,
        "last_name": provider.last_name,
        "phone_number": provider.phone_number,
        "dob": provider.dob,
        "gender": provider.gender,
        "license_number": provider.license_number,
        "specialty": provider.specialty,
        "qualifications": provider.qualifications or {},
        "availability": provider.availability or {},
        "department": provider.department.name if provider.department else None,
        "location": provider.location.name if provider.location else None
    }

@router.get("/{user_id}/patient", response_model=PatientResponse)
async def get_patient_by_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    result = await db.execute(
        select(Patient)
        .options(
            selectinload(Patient.clinic),
            selectinload(Patient.location),
            selectinload(Patient.department)
        )
        .where(Patient.user_id == user_id)
    )
    patient = result.scalar()

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found for this user"
        )

    return {
        "id": patient.id,
        "first_name": patient.first_name,
        "last_name": patient.last_name,
        "phone_number": patient.phone_number,
        "date_of_birth": patient.date_of_birth,
        "gender": patient.gender,
        "encrypted_ssn": patient.encrypted_ssn,
        "insurance_provider": patient.insurance_provider,
        "policy_number": patient.policy_number,
        "clinic": patient.clinic.name if patient.clinic else None,
        "location": patient.location.name if patient.location else None,
        "department": patient.department.name if patient.department else None

    }