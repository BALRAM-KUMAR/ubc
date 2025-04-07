# main.py

from fastapi import APIRouter
from core_app import create_app
# from .modules import auth, tenants, appointments
from modules.routes import auth, subscription, landing_page, patients, appointment, location, user_created_by_admin, department, clinic

app = create_app()

# Routes
app.include_router(auth.router)
app.include_router(subscription.router)
app.include_router(patients.router)
app.include_router(landing_page.router)
app.include_router(appointment.router)
app.include_router(clinic.router)
app.include_router(location.router)
app.include_router(department.router)
app.include_router(user_created_by_admin.router)

@app.get("/health")
async def health_check():
    return {"status": "ok"}
