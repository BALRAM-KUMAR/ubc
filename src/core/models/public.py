from sqlalchemy import Column,event, Integer, String, Boolean, DateTime, ForeignKey, JSON, Text,CheckConstraint, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from core.database import PublicBase

# --------------------------
# Tenant Management
# --------------------------
class Tenant(PublicBase):
    __tablename__ = "tenants"
    __table_args__ = (
        # CheckConstraint("plan_id IN (SELECT id FROM public.plan)", name="valid_plan"),
        Index("idx_tenants_plan_id", "plan_id"),
        {"schema": "public"},
    )

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)  
    subdomain = Column(String(50), unique=True)  
    custom_domain = Column(String(100), unique=True)
    plan_id = Column(Integer, ForeignKey("public.plan.id"), nullable=False)

    # Tenant Status & Configuration
    is_active = Column(Boolean, default=False)
    setup_stage = Column(String(20), default='initial')  # initial, org_setup, billing_config, completed
    healthcare_type = Column(String(50))  # hospital, clinic, diagnostic_center
    timezone = Column(String(50), default='UTC')
    compliance_settings = Column(JSON)  # HIPAA/HITECH configurations
    accepted_insurances = Column(JSON)  # List of accepted insurance providers
    onboarding_data = Column(JSON)  # Store partial setup progress
    
    # Subscription Management
    subscription_id = Column(String(100), unique=True)
    payment_status = Column(String(20), default="pending")
    next_billing_date = Column(DateTime, nullable=True)
    current_period_start = Column(DateTime)
    current_period_end = Column(DateTime)
    gateway_customer_id = Column(String(100))
    
    created_at = Column(DateTime, server_default=func.now())    
    plan = relationship("Plan", back_populates="tenants")
    transactions = relationship("Transaction", back_populates="tenant")
    testimonials = relationship("TenantTestimonials", back_populates="tenant", cascade="all, delete-orphan")
   

class Plan(PublicBase):
    __tablename__ = "plan"
    __table_args__ = {"schema": "public"}

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)  
    price = Column(Integer, nullable=False)
    features = Column(JSON)  # {"ehr": True, "telemedicine": False}
    recommended = Column(Boolean, default=False)
    max_users = Column(Integer, default=10)
    
    tenants = relationship("Tenant", back_populates="plan")

# --------------------------
# Transaction Management
# --------------------------
class Transaction(PublicBase):
    __tablename__ = "transactions"
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'completed', 'failed', 'refunded')", name="valid_status"),
        {"schema": "public"}
    )
    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("public.tenants.id"), nullable=False)
    amount = Column(Integer, nullable=False)  # In cents
    currency = Column(String(10), default="USD")
    payment_gateway = Column(String(50), nullable=False)
    transaction_id = Column(String(100), unique=True)
    status = Column(String(20), nullable=False)
    invoice_id = Column(String(100))
    receipt_url = Column(Text)
    tmetadata = Column(JSON)  # Renamed from T_metadata
    created_at = Column(DateTime, server_default=func.now())

    tenant = relationship("Tenant", back_populates="transactions", foreign_keys=[tenant_id])



# --------------------------
# Security & Compliance
# --------------------------
class AuditLog(PublicBase):
    __tablename__ = "audit_logs"
    __table_args__ = {"schema": "public"}
    
    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("public.tenants.id"))
    action = Column(String(100))  # e.g., "patient_record_accessed"
    timestamp = Column(DateTime, server_default=func.now())
    ip_address = Column(String(45))  # Added for security tracking
    details = Column(JSON)
    tenant = relationship("Tenant", foreign_keys=[tenant_id])

    
class Language(PublicBase):
    __tablename__ ="languages"
    __table_args__ = {"schema":"public"}

    id = Column(Integer, primary_key=True)
    name = Column(String(150), unique=True, nullable=False)  # Added nullable
    request_language = Column(String(150))
    description = Column(String(500))  
    
class ComplianceImplemented(PublicBase):
    __tablename__ ="compliance"
    __table_args__ = (
        Index("idx_compliance_name", "name"),
        {"schema": "public"}
    )
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False, index=True)  # Increased length + index
    details = Column(JSON, nullable=False)  # Enforced non-null constraint
    description = Column(String(500)) 


class TenantTestimonials(PublicBase):
    __tablename__ = "tenanttestimonials"
    __table_args__ = {"schema": "public"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(Integer, ForeignKey("public.tenants.id", ondelete="CASCADE"), nullable=False)
    feedback = Column(Text, nullable=False)  # Allow long-form feedback
    rating = Column(Integer, CheckConstraint("rating BETWEEN 1 AND 5"), nullable=False)  # 1 to 5 stars rating
    is_approved = Column(Boolean, default=False)  # Admin approval system
    created_at = Column(DateTime, server_default=func.now())

    # Relationship with Tenant
    tenant = relationship("Tenant", back_populates="testimonials")





class FAQQuestion(PublicBase):
    __tablename__ = "faq_questions"
    __table_args__ = {"schema": "public"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    question = Column(String(1000), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    answers = relationship("FAQAnswer", back_populates="question", cascade="all, delete-orphan")
    comments = relationship("FAQComment", back_populates="question", cascade="all, delete-orphan")
    likes = relationship("FAQLike", back_populates="question", cascade="all, delete-orphan")

class FAQAnswer(PublicBase):
    __tablename__ = "faq_answers"
    __table_args__ = {"schema": "public"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    question_id = Column(Integer, ForeignKey("public.faq_questions.id", ondelete="CASCADE"), nullable=False)
    answer = Column(String(10000), nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    question = relationship("FAQQuestion", back_populates="answers")
    comments = relationship("FAQComment", back_populates="answer", cascade="all, delete-orphan")
    likes = relationship("FAQLike", back_populates="answer", cascade="all, delete-orphan")

class FAQComment(PublicBase):
    __tablename__ = "faq_comments"
    __table_args__ = {"schema": "public"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    question_id = Column(Integer, ForeignKey("public.faq_questions.id", ondelete="CASCADE"), nullable=True)
    answer_id = Column(Integer, ForeignKey("public.faq_answers.id", ondelete="CASCADE"), nullable=True)
    comment = Column(String(10000), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    question = relationship("FAQQuestion", back_populates="comments")
    answer = relationship("FAQAnswer", back_populates="comments")

class FAQLike(PublicBase):
    __tablename__ = "faq_likes"
    __table_args__ = {"schema": "public"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    question_id = Column(Integer, ForeignKey("public.faq_questions.id", ondelete="CASCADE"), nullable=True)
    answer_id = Column(Integer, ForeignKey("public.faq_answers.id", ondelete="CASCADE"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    question = relationship("FAQQuestion", back_populates="likes")
    answer = relationship("FAQAnswer", back_populates="likes")
 

# Benefits of This FAQ design Design 
#  Supports multiple answers per question.
#  Supports nested comments for both questions & answers.
#  Supports likes for both questions & answers.
#  Scalable & optimized for queries.

# Example AuditLog entry for payment
# {
#   "action": "subscription_created",
#   "details": {
#     "plan": "pro",
#     "subscription_id": "sub_xxx",
#     "amount": 2999,
#     "currency": "USD"
#   }
# }