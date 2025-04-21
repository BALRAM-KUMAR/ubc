from sqlalchemy import Column, Index, event, Integer, String, Boolean, DateTime, ForeignKey, Text, JSON, text
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func
from core.database import TenantAwareBase, tenant_schema
from core.models.public import Tenant

# --------------------------
# Role-Based Access Control
# --------------------------
class Role(TenantAwareBase):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False)  # Removed unique=True since it's per-tenant
    permissions = Column(JSON)
    is_custom = Column(Boolean, default=False)
    users = relationship("User", back_populates="role")



class User(TenantAwareBase):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(30))
    email = Column(String(100), unique=True)
    password_hash = Column(String(200))
    role_id = Column(Integer, ForeignKey('roles.id'))  # Now points to tenant-local roles
    tenant_id = Column(Integer ,nullable=False, index=True)  # No FK
    
    # Security Features
    mfa_enabled = Column(Boolean, default=False)
    last_password_change = Column(DateTime)
    invitation_token = Column(String(100))
    invitation_status = Column(String(20), default='pending')
    
    # Status Tracking
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())

    patients = relationship("Patient", back_populates="user")
    role = relationship("Role", back_populates="users")
    providers = relationship("Provider", back_populates="user")


    
# --------------------------
# Organization Structure
# --------------------------
class Clinic(TenantAwareBase):
    __tablename__ = "clinics"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True)
    description = Column(Text)
    operating_hours = Column(JSON)  # JSON structure for weekly hours
    created_at = Column(DateTime, server_default=func.now())
    
    locations = relationship("Location", back_populates="clinic", cascade="all, delete-orphan")
    departments = relationship("Department", back_populates="clinic")


class Location(TenantAwareBase):
    __tablename__ = "locations"
    id = Column(Integer, primary_key=True)
    clinic_id = Column(Integer, ForeignKey("clinics.id"), nullable=False)
    name = Column(String(100))
    address = Column(String(255))
    city = Column(String(100))
    state = Column(String(100))
    zip_code = Column(String(20))
    google_map_link = Column(String(200))
    phone = Column(String(20))  # Added contact information
    
    clinic = relationship("Clinic", back_populates="locations")
    departments = relationship("Department", back_populates="location")
    providers = relationship("Provider", back_populates="location")

class Department(TenantAwareBase):
    __tablename__ = "departments"
    id = Column(Integer, primary_key=True)
    clinic_id = Column(Integer, ForeignKey("clinics.id"))
    location_id = Column(Integer, ForeignKey("locations.id"))
    name = Column(String(100), unique=True)
    description = Column(Text)
    required_roles = Column(JSON)  # Roles allowed in this department
    
    clinic = relationship("Clinic", back_populates="departments")
    location = relationship("Location", back_populates="departments")
    providers = relationship("Provider", back_populates="department")



# --------------------------
# Staff Management
# --------------------------
class Provider(TenantAwareBase):
    __tablename__ = "providers"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    department_id = Column(Integer, ForeignKey("departments.id"))
    location_id = Column(Integer, ForeignKey("locations.id"))
    #basic deatisl
    first_name = Column(String(50))
    last_name = Column(String(50))
    phone_number = Column(String(20))
    dob = Column(DateTime)
    gender = Column(String(20))
    fee = Column(Integer)
    currency = Column(String(30))
    # Professional Details
    license_number = Column(String(100))  # Encrypted
    specialty = Column(String(100))
    qualifications = Column(JSON)  # [{"degree": "MD", "year": 2010}]
    availability = Column(JSON)  # Recurring schedule
    
    # Relationships
    user = relationship("User", back_populates="providers")
    department = relationship("Department", back_populates="providers")
    location = relationship("Location", back_populates="providers")
    appointments = relationship("Appointment", back_populates="provider")
    medical_history = relationship("MedicalHistory", back_populates="provider")
    prescriptions = relationship("Prescription", back_populates="provider")


 # --------------------------
# Patient Management
# --------------------------
class Patient(TenantAwareBase):
    __tablename__ = "patients"
    id = Column(Integer, primary_key=True)
    first_name = Column(String(50))
    last_name = Column(String(50))
    patient_type = Column(String(50))  # 'self' or 'other'
    relationship_to_user = Column(String(50), nullable=True)  # New field

    phone_number = Column(String(20))
    date_of_birth = Column(DateTime)
    gender = Column(String(20))
    encrypted_ssn = Column(String(200))
    insurance_provider = Column(String(100))
    policy_number = Column(String(100))
    
    user_id = Column(Integer, ForeignKey("users.id"))
    primary_care_id = Column(Integer, ForeignKey("providers.id"))

    user = relationship("User", back_populates="patients")  
    appointments = relationship("Appointment", back_populates="patient")
    medical_history = relationship("MedicalHistory", back_populates="patient")
    insurance_claims = relationship("InsuranceClaim", back_populates="patient")
    invoices = relationship("Invoice", back_populates="patient")

    __table_args__ = (
        Index(
            'uq_user_self_patient',
            'user_id',
            'patient_type',
            unique=True,
            postgresql_where=text("patient_type = 'self'")
        ),
    )

    @validates('patient_type')
    def validate_patient_type(self, key, patient_type):
        allowed = ['self', 'other']
        if patient_type not in allowed:
            raise ValueError(f"Invalid patient type. Allowed: {allowed}")
        if patient_type == 'self':
            existing = self.query.filter_by(
                user_id=self.user_id,
                patient_type='self'
            ).first()
            if existing and existing.id != self.id:
                raise ValueError("User can only have one 'self' patient")
        return patient_type
    

class MedicalHistory(TenantAwareBase):
    __tablename__ = "medical_history"
    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    provider_id = Column(Integer, ForeignKey("providers.id"))
    diagnosis = Column(Text)
    treatment = Column(Text)
    prescriptions = Column(JSON) 
    visit_date = Column(DateTime)
    
    patient = relationship("Patient", back_populates="medical_history")
    provider = relationship("Provider", back_populates="medical_history")



# --------------------------
# Appointment Management
# --------------------------
class Appointment(TenantAwareBase):
    __tablename__ = "appointments"
    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    provider_id = Column(Integer, ForeignKey("providers.id"))
    location_id = Column(Integer, ForeignKey("locations.id"))  # Clinic Location
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    service_id = Column(Integer, ForeignKey("services.id"), nullable=True)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    status = Column(String(20))  # "scheduled", "completed", "canceled"
    notes = Column(Text)
    video_url = Column(String(200))  # For telehealth

    cancellation_reason = Column(Text, nullable=True)

    rescheduled_from_id = Column(Integer, ForeignKey("appointments.id"), nullable=True)

    # Relationships
    patient = relationship("Patient", back_populates="appointments")
    provider = relationship("Provider", back_populates="appointments")
    location = relationship("Location")
    department = relationship("Department")
    service = relationship("Service", back_populates="appointments")
    reminders = relationship("AppointmentReminder", back_populates="appointment")
    rescheduled_from = relationship("Appointment", remote_side=[id], backref="rescheduled_to")

class AppointmentReminder(TenantAwareBase):
    __tablename__ = "appointment_reminders"
    id = Column(Integer, primary_key=True)
    appointment_id = Column(Integer, ForeignKey("appointments.id"))
    reminder_type = Column(String(20))  # "sms", "email"
    scheduled_at = Column(DateTime)  # When the reminder should be sent
    status = Column(String(20))  # "pending", "sent", "failed"

    # Relationships
    appointment = relationship("Appointment", back_populates="reminders")

#waitlist functionality
class Waitlist(TenantAwareBase):
    __tablename__ = "waitlist"
    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    provider_id = Column(Integer, ForeignKey("providers.id"))
    location_id = Column(Integer, ForeignKey("locations.id"))
    preferred_time = Column(DateTime)  # Patient's preferred time
    status = Column(String(20))  # "waiting", "notified", "removed"

    # Relationships
    patient = relationship("Patient")
    provider = relationship("Provider")
    location = relationship("Location")

#Clinics may offer different services (e.g., general consultation, surgery, diagnostics).
#Multiple Services (Specialized Appointments)
class Service(TenantAwareBase):
    __tablename__ = "services"
    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    description = Column(Text)
    department_id = Column(Integer, ForeignKey("departments.id"))
    duration = Column(Integer)  # Minutes
    cost = Column(Integer)  # In cents
    appointments = relationship("Appointment", back_populates="service")
    department = relationship("Department")

# #Clinics may offer different services (e.g., general consultation, surgery, diagnostics).
# #Multiple Services (Specialized Appointments)
# class Service(TenantAwareBase):
#     __tablename__ = "services"

#     id = Column(Integer, primary_key=True)
#     name = Column(String(100))
#     description = Column(Text)
#     department_id = Column(Integer, ForeignKey("departments.id"))

#     # Relationships
#     department = relationship("Department")
#     appointments = relationship("Appointment", back_populates="service")




# --------------------------
# Billing & Insurance
# --------------------------
class Invoice(TenantAwareBase):
    __tablename__ = "invoices"
    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    appointment_id = Column(Integer, ForeignKey("appointments.id"))
    amount = Column(Integer)
    status = Column(String(20))  # Generated, sent, paid
    due_date = Column(DateTime)
    insurance_covered = Column(Boolean, default=False)
    
    patient = relationship("Patient", back_populates="invoices")
    appointment = relationship("Appointment")


class InsuranceClaim(TenantAwareBase):
    __tablename__ = "insurance_claims"
    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    invoice_id = Column(Integer, ForeignKey("invoices.id"))
    status = Column(String(20))  # submitted, approved, rejected
    processed_date = Column(DateTime)
    
    patient = relationship("Patient", back_populates="insurance_claims")


# --------------------------
# Clinical Operations
# --------------------------
class MedicalCode(TenantAwareBase):
    __tablename__ = "medical_codes"
    id = Column(Integer, primary_key=True)
    code_type = Column(String(20))  # ICD10, CPT, LOINC
    code = Column(String(20))
    description = Column(Text)
    effective_date = Column(DateTime)

# class MedicalCode(TenantAwareBase):
#     __tablename__ = "medical_codes"
    
#     id = Column(Integer, primary_key=True)
#     tenant_id = Column(Integer, ForeignKey("public.tenants.id"))
#     code_type = Column(String(20))  # ICD10, CPT
#     code = Column(String(20))
#     description = Column(Text)
    
#     tenant = relationship("Tenant", back_populates="medical_codes")

class Prescription(TenantAwareBase):
    __tablename__ = "prescriptions"
    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    medication = Column(JSON)  # Structured drug information
    dosage = Column(String(100))
    refills = Column(Integer)
    prescribed_by = Column(Integer, ForeignKey("providers.id"))
    
    patient = relationship("Patient")
    provider = relationship("Provider", back_populates="prescriptions")

    
# --------------------------
# Telemedicine
# --------------------------
class TelemedicineSession(TenantAwareBase):
    __tablename__ = "telemedicine_sessions"
    id = Column(Integer, primary_key=True)
    appointment_id = Column(Integer, ForeignKey("appointments.id"))
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    recording_url = Column(String(200))  # Encrypted S3 URL
    participants = Column(JSON)  # {"patient_id": 1, "doctor_id": 2}

# --------------------------
# Inventory Management
# --------------------------
class InventoryItem(TenantAwareBase):
    __tablename__ = "inventory_items"
    id = Column(Integer, primary_key=True)
    name = Column(String(100))  # e.g., "Bandages"
    description = Column(Text)
    quantity = Column(Integer)
    supplier = Column(String(100))
    last_restocked = Column(DateTime)