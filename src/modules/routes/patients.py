# app/routers/patients.py
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel, EmailStr
from datetime import date
from typing import List, Optional
from datetime import datetime
from core.dependencies import get_tenant_user, get_db
from core.models.public import AuditLog
from core.models.tenant import Patient,User

router = APIRouter(
    prefix="/patients",
    tags=["patients"],
    dependencies=[Depends(get_tenant_user)]
)

# Pydantic Models
class PatientBase(BaseModel):
    first_name: str
    last_name: str
    date_of_birth: date
    gender: str
    insurance_provider: Optional[str] = None
    policy_number: Optional[str] = None

class PatientCreate(PatientBase):
    encrypted_ssn: str  # Should come from secure encryption in frontend

class PatientUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    insurance_provider: Optional[str] = None
    policy_number: Optional[str] = None

class PatientResponse(PatientBase):
    id: int
    created_at: datetime
    
    class Config:
        orm_mode = True

# CRUD Endpoints
@router.post("/", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
async def create_patient(
    patient_data: PatientCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_tenant_user)
):
    # Role check
    # if user.role.name not in ["clinic_admin", "staff"]:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Insufficient permissions for patient creation"
    #     )
    
    # Create patient
    new_patient = Patient(**patient_data.dict())
    db.add(new_patient)
    await db.commit()
    await db.refresh(new_patient)

    # Audit log
    audit_log = AuditLog(
        tenant_id=request.state.tenant.id,
        user_id=user.id,
        action="patient_created",
        details={
            "patient_id": new_patient.id,
            "insurance_provider": new_patient.insurance_provider
        }
    )
    db.add(audit_log)
    await db.commit()

    return new_patient

@router.get("/{patient_id}", response_model=PatientResponse)
async def get_patient(
    patient_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_tenant_user)
):
    result = await db.execute(
        select(Patient).where(Patient.id == patient_id))
    patient = result.scalar_one_or_none()
    
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found"
        )
    
    return patient

@router.patch("/{patient_id}", response_model=PatientResponse)
async def update_patient(
    patient_id: int,
    update_data: PatientUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_tenant_user)
):
    # if user.role.name not in ["clinic_admin", "staff"]:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Insufficient permissions for updates"
    #     )

    result = await db.execute(select(Patient).where(Patient.id == patient_id))
    patient = result.scalar_one_or_none()
    
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Update fields
    for key, value in update_data.dict(exclude_unset=True).items():
        setattr(patient, key, value)
    
    await db.commit()
    await db.refresh(patient)

    # Audit log
    audit_log = AuditLog(
        tenant_id=request.state.tenant.id,
        user_id=user.id,
        action="patient_updated",
        details={"patient_id": patient_id}
    )
    db.add(audit_log)
    await db.commit()

    return patient

@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_patient(
    patient_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_tenant_user)
):
    if user.role.name != "clinic_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only clinic admins can delete patients"
        )

    result = await db.execute(select(Patient).where(Patient.id == patient_id))
    patient = result.scalar_one_or_none()
    
    if patient:
        await db.delete(patient)
        await db.commit()

        # Audit log
        audit_log = AuditLog(
            tenant_id=request.state.tenant.id,
            user_id=user.id,
            action="patient_deleted",
            details={"patient_id": patient_id}
        )
        db.add(audit_log)
        await db.commit()

@router.get("/", response_model=List[PatientResponse])
async def list_patients(
    search: Optional[str] = None,
    insurance_provider: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_tenant_user)
):
    query = select(Patient)
    
    if search:
        query = query.where(
            Patient.first_name.ilike(f"%{search}%") |
            Patient.last_name.ilike(f"%{search}%")
        )
    
    if insurance_provider:
        query = query.where(
            Patient.insurance_provider.ilike(f"%{insurance_provider}%")
        )

    result = await db.execute(query.offset(skip).limit(limit))
    patients = result.scalars().all()
    return patients