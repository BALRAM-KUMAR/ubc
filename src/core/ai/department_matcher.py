# core/ai/department_matcher.py
from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List
from fastapi import Depends, HTTPException, APIRouter
from core.models.tenant import Department, Provider, Appointment
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from core.dependencies import get_db

class DepartmentMatcher:
    def __init__(self):
        self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        self.department_cache = []

    async def load_departments(self, db: AsyncSession):
        """Load and cache departments with their embeddings"""
        result = await db.execute(select(Department))
        departments = result.scalars().all()

        self.department_cache.clear()
        texts = []
        for dept in departments:
            text = dept.name if not dept.description else f"{dept.name}: {dept.description}"
            self.department_cache.append({
                "id": dept.id,
                "text": text,
                "embedding": None
            })
            texts.append(text)

        embeddings = self.model.encode(texts, convert_to_tensor=True)
        for i, emb in enumerate(embeddings):
            self.department_cache[i]["embedding"] = emb.cpu().numpy()

    async def find_best_department(self, user_input: str) -> int:
        """Find most relevant department using semantic similarity"""
        if not self.department_cache:
            raise ValueError("Departments not loaded")

        input_embedding = self.model.encode(user_input, convert_to_tensor=True).cpu().numpy()

        similarities = [
            (dept["id"], np.dot(input_embedding, dept["embedding"]))
            for dept in self.department_cache
        ]

        best_match = max(similarities, key=lambda x: x[1])
        return best_match[0]

router = APIRouter(prefix="/a", tags=["appointment"])

from datetime import datetime, timedelta
from sqlalchemy.orm import selectinload
from typing import Optional
from fastapi import Query, HTTPException
from typing import Optional
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

@router.get("/auto-find-doctors")
async def auto_find_doctors(
    symptoms: Optional[str] = Query(default=None),
    patient_id: int = Query(...),
    db: AsyncSession = Depends(get_db)
):
    matcher = DepartmentMatcher()
    await matcher.load_departments(db)

    if symptoms:
        try:
            best_dept_id = await matcher.find_best_department(symptoms)

            # Fetch providers in the best department
            provider_query = (
                select(Provider)
                .where(Provider.department_id == best_dept_id)
                .options(
                    selectinload(Provider.department),
                    selectinload(Provider.location),
                )
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    else:
        # No symptoms: fetch all providers from all departments
        provider_query = (
            select(Provider)
            .options(
                selectinload(Provider.department),
                selectinload(Provider.location),
            )
        )

    provider_result = await db.execute(provider_query)
    providers = provider_result.scalars().all()

    # Fetch patient's appointments
    patient_appt_query = select(Appointment).where(Appointment.patient_id == patient_id)
    patient_appt_result = await db.execute(patient_appt_query)
    patient_appointments = patient_appt_result.scalars().all()
    patient_busy = [(appt.start_time, appt.end_time) for appt in patient_appointments]

    providers_with_availability = []

    for provider in providers:
        # Fetch provider's appointments
        provider_appt_query = select(Appointment).where(Appointment.provider_id == provider.id)
        provider_appt_result = await db.execute(provider_appt_query)
        provider_appointments = provider_appt_result.scalars().all()
        provider_busy = [(appt.start_time, appt.end_time) for appt in provider_appointments]

        # Calculate available slots (simplified example; adjust based on your availability structure)
        available_slots = []
        # Assuming availability is a list of time slots; adjust parsing as needed
        # This example checks next 7 days for 30-minute slots starting from the next hour
        now = datetime.now()
        for day in range(7):
            current_date = now + timedelta(days=day)
            # Example: Provider is available 9 AM to 5 PM each day
            start_time = datetime(current_date.year, current_date.month, current_date.day, 9, 0)
            end_time = datetime(current_date.year, current_date.month, current_date.day, 17, 0)
            current_slot = start_time
            while current_slot < end_time:
                slot_end = current_slot + timedelta(minutes=30)
                # Check if slot is free for provider
                provider_free = True
                for busy_start, busy_end in provider_busy:
                    if not (slot_end <= busy_start or current_slot >= busy_end):
                        provider_free = False
                        break
                if provider_free:
                    # Check if patient is free
                    patient_free = True
                    for p_start, p_end in patient_busy:
                        if not (slot_end <= p_start or current_slot >= p_end):
                            patient_free = False
                            break
                    if patient_free:
                        available_slots.append({
                            "start": current_slot,
                            "end": slot_end
                        })
                current_slot = slot_end

        if available_slots:
            # Sort available slots by start time
            available_slots.sort(key=lambda x: x["start"])
            providers_with_availability.append({
                "provider": provider,
                "available_slots": available_slots
            })

    return providers_with_availability