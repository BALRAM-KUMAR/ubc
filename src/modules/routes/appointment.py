# app/routers/appointments.py
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from pydantic import BaseModel, validator
from datetime import datetime, timedelta
from typing import List, Optional
from core.dependencies import get_tenant_user, get_db
from core.models.tenant import Appointment, AppointmentReminder, Waitlist, Patient, Provider, Service, User
from core.models.public import AuditLog


from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from icalendar import Calendar, Event
import json

router = APIRouter(
    prefix="/appointments",
    tags=["appointments"],
    dependencies=[Depends(get_tenant_user)]
)

# Pydantic Models
class AppointmentBase(BaseModel):
    patient_id: int
    provider_id: int
    location_id: int
    service_id: Optional[int] = None
    start_time: datetime
    duration: int  # In minutes

class AppointmentCreate(AppointmentBase):
    @validator('start_time')
    def validate_future_date(cls, v):
        if v < datetime.now() + timedelta(minutes=15):
            raise ValueError("Appointments must be scheduled at least 15 minutes in advance")
        return v

class AppointmentUpdate(BaseModel):
    new_start_time: Optional[datetime] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    cancellation_reason: Optional[str] = None

class AppointmentResponse(AppointmentBase):
    id: int
    end_time: datetime
    status: str
    created_at: datetime
    patient_name: str
    provider_name: str
    location_name: str
    
    class Config:
        from_attributes = True

# Core Business Logic Components
class AppointmentManager:
    @staticmethod
    async def check_availability(
        db: AsyncSession,
        provider_id: int,
        start_time: datetime,
        duration: int
    ):
        end_time = start_time + timedelta(minutes=duration)
        
        # Check existing appointments
        result = await db.execute(
            select(Appointment).where(
                (Appointment.provider_id == provider_id) &
                ((Appointment.start_time < end_time) &
                (Appointment.end_time > start_time)) &
                (Appointment.status.in_(["scheduled", "rescheduled"]))
            )
        )
        return not result.scalars().first()

    @staticmethod
    def validate_clinic_hours(start_time: datetime):
        hour = start_time.hour
        if not (9 <= hour < 17):
            raise HTTPException(
                status_code=400,
                detail="Appointments must be between 9AM and 5PM"
            )

# Helper Functions
async def schedule_reminders(appointment: Appointment, db: AsyncSession):
    reminder_times = [
        (appointment.start_time - timedelta(hours=24), "email"),
        (appointment.start_time - timedelta(hours=1), "sms")
    ]
    
    for remind_at, reminder_type in reminder_times:
        reminder = AppointmentReminder(
            appointment_id=appointment.id,
            reminder_type=reminder_type,
            scheduled_at=remind_at,
            status="pending"
        )
        db.add(reminder)
    await db.commit()

async def handle_waitlist(appointment: Appointment, db: AsyncSession):
    # Get first waitlist entry
    result = await db.execute(
        select(Waitlist).where(
            (Waitlist.provider_id == appointment.provider_id) &
            (Waitlist.location_id == appointment.location_id) &
            (Waitlist.status == "waiting")
        ).order_by(Waitlist.created_at).limit(1)
    )
    next_patient = result.scalar()
    
    if next_patient:
        # Create new appointment
        new_appt = Appointment(
            patient_id=next_patient.patient_id,
            provider_id=appointment.provider_id,
            location_id=appointment.location_id,
            start_time=appointment.start_time,
            duration=(appointment.end_time - appointment.start_time).seconds // 60,
            status="scheduled",
            created_by=0  # System-generated
        )
        
        db.add(new_appt)
        next_patient.status = "notified"
        await db.commit()


# API Endpoints
@router.post("/", response_model=AppointmentResponse, status_code=201)
async def create_appointment(
    appointment: AppointmentCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_tenant_user)
):
    # Authorization
    if user.role.name not in ["clinic_admin", "staff"]:
        raise HTTPException(403, "Insufficient permissions")

    # Check provider exists
    provider = await db.get(Provider, appointment.provider_id)
    if not provider:
        raise HTTPException(404, "Provider not found")

    # Check patient exists
    patient = await db.get(Patient, appointment.patient_id)
    if not patient:
        raise HTTPException(404, "Patient not found")

    # Availability check
    if not await AppointmentManager.check_availability(
        db,
        appointment.provider_id,
        appointment.start_time,
        appointment.duration
    ):
        raise HTTPException(409, "Time slot unavailable")

    # Create appointment
    end_time = appointment.start_time + timedelta(minutes=appointment.duration)
    new_appt = Appointment(
        **appointment.dict(),
        end_time=end_time,
        status="scheduled",
        created_by=user.id
    )
    
    db.add(new_appt)
    await db.commit()
    await db.refresh(new_appt)

    # Create audit log
    audit_log = AuditLog(
        tenant_id=request.state.tenant.id,
        user_id=user.id,
        action="appointment_created",
        details={
            "appointment_id": new_appt.id,
            "provider": provider.full_name,
            "patient": patient.full_name
        }
    )
    db.add(audit_log)
    await db.commit()

    # Schedule reminders
    await schedule_reminders(new_appt, db)
    
    return new_appt

@router.patch("/{appointment_id}", response_model=AppointmentResponse)
async def update_appointment(
    appointment_id: int,
    update_data: AppointmentUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_tenant_user)
):
    appt = await db.get(Appointment, appointment_id)
    if not appt:
        raise HTTPException(404, "Appointment not found")

    # Status transition validation
    if update_data.status:
        valid_transitions = {
            "scheduled": ["rescheduled", "canceled"],
            "rescheduled": ["canceled"],
            "canceled": []
        }
        if update_data.status not in valid_transitions.get(appt.status, []):
            raise HTTPException(400, "Invalid status transition")

    # Handle cancellation
    if update_data.status == "canceled":
        if appt.start_time < datetime.now() + timedelta(hours=24):
            if user.role.name != "clinic_admin":
                raise HTTPException(403, "Cancellations within 24hr require admin approval")
        
        # Process waitlist
        await handle_waitlist(appt, db)

    # Update fields
    for key, value in update_data.dict(exclude_unset=True).items():
        setattr(appt, key, value)
    
    await db.commit()
    await db.refresh(appt)

    # Audit log
    audit_log = AuditLog(
        tenant_id=request.state.tenant.id,
        user_id=user.id,
        action="appointment_updated",
        details={"appointment_id": appointment_id}
    )
    db.add(audit_log)
    await db.commit()

    return appt

@router.get("/availability/{provider_id}")
async def check_availability(
    provider_id: int,
    start_time: datetime,
    end_time: datetime,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_tenant_user)
):
    # Convert to time slots
    duration = (end_time - start_time).total_seconds() / 60
    available = await AppointmentManager.check_availability(
        db, provider_id, start_time, duration
    )
    return {"available": available}

# Waitlist Integration
@router.post("/waitlist")
async def add_to_waitlist(
    patient_id: int,
    provider_id: int,
    location_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_tenant_user)
):
    # Check existing waitlist entry
    existing = await db.execute(
        select(Waitlist).where(
            (Waitlist.patient_id == patient_id) &
            (Waitlist.provider_id == provider_id)
        ))
    if existing.scalar():
        raise HTTPException(400, "Already on waitlist")

    waitlist_entry = Waitlist(
        patient_id=patient_id,
        provider_id=provider_id,
        location_id=location_id,
        preferred_time=datetime.now() + timedelta(days=1),
        status="waiting"
    )
    
    db.add(waitlist_entry)
    await db.commit()
    return {"status": "added_to_waitlist"}



# Color configuration for statuses
STATUS_COLORS = {
    "scheduled": "#2196F3",
    "completed": "#4CAF50",
    "canceled": "#F44336",
    "rescheduled": "#FF9800",
    "available": "#8BC34A"
}

class CalendarEvent(BaseModel):
    id: int
    title: str
    start: datetime
    end: datetime
    type: str
    color: str
    participants: Optional[List[str]] = None
    status: Optional[str] = None
    location: Optional[str] = None
    notes: Optional[str] = None
    can_edit: bool = False
    conflict: bool = False

# Helper functions
async def check_appointment_conflict(
    db: AsyncSession,
    appointment: Appointment,
    new_start: datetime = None,
    new_end: datetime = None
) -> bool:
    start = new_start or appointment.start_time
    end = new_end or appointment.end_time
    
    conflict_query = select(Appointment).where(
        (Appointment.provider_id == appointment.provider_id) &
        (Appointment.id != appointment.id) &
        (Appointment.start_time < end) &
        (Appointment.end_time > start)
    )
    
    result = await db.execute(conflict_query)
    return result.scalars().first() is not None

def get_event_title(appointment: Appointment, user: User) -> str:
    if user.role.name == "provider":
        return f"{appointment.patient.first_name} {appointment.patient.last_name[:1]}"
    if user.role.name == "patient":
        return f"Dr. {appointment.provider.last_name}"
    return f"{appointment.patient.full_name} - {appointment.provider.full_name}"

def check_edit_permissions(user: User, appointment: Appointment) -> bool:
    if user.role.name in ["clinic_admin", "staff"]:
        return True
    if user.role.name == "provider" and appointment.provider_id == user.provider_id:
        return appointment.status == "scheduled"
    return False

async def get_provider_availability(
    start_date: datetime,
    end_date: datetime,
    db: AsyncSession
) -> List[CalendarEvent]:
    providers = await db.execute(select(Provider))
    availability_events = []
    
    for provider in providers.scalars():
        current_date = start_date
        while current_date <= end_date:
            if current_date.weekday() < 5:  # Mon-Fri
                start_time = current_date.replace(hour=9, minute=0)
                end_time = current_date.replace(hour=17, minute=0)
                availability_events.append(CalendarEvent(
                    title="Available",
                    start=start_time,
                    end=end_time,
                    type="availability",
                    color=STATUS_COLORS["available"],
                    status="available"
                ))
            current_date += timedelta(days=1)
    
    return availability_events

async def create_audit_log(request, user, action, details, db):
    audit_log = AuditLog(
        tenant_id=request.state.tenant.id,
        user_id=user.id,
        action=action,
        details=details
    )
    db.add(audit_log)
    await db.commit()

@router.get("/calendar", response_model=List[CalendarEvent])
async def get_calendar_view(
    start_date: datetime = Query(..., description="Start date in UTC"),
    end_date: datetime = Query(..., description="End date in UTC"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_tenant_user)
):
    # Validate date range
    if (end_date - start_date).days > 93:
        raise HTTPException(400, "Date range cannot exceed 3 months")
    
    base_query = select(Appointment).where(
        Appointment.start_time >= start_date,
        Appointment.end_time <= end_date
    )

    # Role-based filtering
    if user.role.name == "patient":
        base_query = base_query.where(Appointment.patient_id == user.patient_id)
    elif user.role.name == "provider":
        base_query = base_query.where(Appointment.provider_id == user.provider_id)

    # Execute query
    result = await db.execute(
        base_query.options(
            selectinload(Appointment.patient),
            selectinload(Appointment.provider),
            selectinload(Appointment.location)
        )
    )
    appointments = result.scalars().all()

    events = []
    for appt in appointments:
        # Check for conflicts
        conflict = await check_appointment_conflict(db, appt)
        
        # Base event setup
        event = CalendarEvent(
            id=appt.id,
            title=get_event_title(appt, user),
            start=appt.start_time,
            end=appt.end_time,
            type="appointment",
            color=STATUS_COLORS.get(appt.status, "#9E9E9E"),
            status=appt.status,
            location=appt.location.name if appt.location else None,
            notes=appt.notes if user.role.name in ["clinic_admin", "staff"] else None,
            can_edit=check_edit_permissions(user, appt),
            conflict=conflict
        )

        # Add participants for admins
        if user.role.name == "clinic_admin":
            event.participants = [
                f"Patient: {appt.patient.full_name}",
                f"Provider: {appt.provider.full_name}"
            ]
        
        events.append(event)

    # Add availability slots for admins/staff
    if user.role.name in ["clinic_admin", "staff"]:
        events += await get_provider_availability(start_date, end_date, db)
    
    return events

@router.patch("/{appointment_id}/reschedule", response_model=CalendarEvent)
async def reschedule_appointment(
    appointment_id: int,
    new_start: datetime,
    new_end: datetime,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_tenant_user)
):
    appt = await db.get(Appointment, appointment_id)
    if not appt:
        raise HTTPException(404, "Appointment not found")

    # # Authorization check
    # if not check_reschedule_permissions(user, appt):
    #     raise HTTPException(403, "Insufficient permissions")

    # Conflict detection
    if await check_appointment_conflict(db, appt, new_start, new_end):
        raise HTTPException(409, "Time slot has conflict")

    # Update appointment
    original_start = appt.start_time
    appt.start_time = new_start
    appt.end_time = new_end
    appt.status = "rescheduled"
    
    # Log and commit
    await create_audit_log(
        request, user, "appointment_rescheduled",
        {"from": original_start.isoformat(), "to": new_start.isoformat()}
    )
    await db.commit()
    
    # Update reminders
    await schedule_reminders(appt, db)
    
    # return await format_calendar_event(appt, user,db)

@router.get("/calendar.ics")
async def export_calendar_ics(
    request: Request,
    start_date: datetime = Query(...),
    end_date: datetime = Query(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_tenant_user)
):
    events = await get_calendar_view(start_date, end_date, db, user)
    
    cal = Calendar()
    cal.add('prodid', '-//Clinic Calendar//mxm.dk//')
    cal.add('version', '2.0')

    for event in events:
        if event.type == "appointment":
            ical_event = Event()
            ical_event.add('uid', f"{event.id}@{request.state.tenant.subdomain}")
            ical_event.add('dtstart', event.start)
            ical_event.add('dtend', event.end)
            ical_event.add('summary', event.title)
            ical_event.add('location', event.location or '')
            ical_event.add('description', json.dumps(event.dict()))
            cal.add_component(ical_event)

    return Response(
        content=cal.to_ical(),
        media_type="text/calendar",
        headers={"Content-Disposition": "attachment; filename=calendar.ics"}
    )

