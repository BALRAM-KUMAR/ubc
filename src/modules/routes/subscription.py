from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta
from core.dependencies import get_db
from core.models.tenant import  User, Role
from core.models.public import Tenant, Transaction, Plan
from ..pydantic_model.subs import TenantCreate, SubscriptionCreate, SubscriptionResponse, UserCreate, UserResponse
from core.security import get_password_hash, create_access_token
from core.dependencies import get_current_user
from core.utils.email_sms import send_credentials_email
from modules.services.razorpay_services import RazorpayService
from core.config import Settings
from sqlalchemy import text
from core.models.tenant import Provider
from core.database import TenantAwareBase, tenant_schema, PublicBase
from core.vault_client import VaultClient
import json
settings = Settings()
vault = VaultClient()

router = APIRouter(prefix="/subscription", tags=["Subscription"])
razorpay_service = RazorpayService()

DEFAULT_ROLES = [
    ('super_admin', '{"ehr_write": true, "appointment_create": false}', False),
    ('clinic_admin', '{"ehr_write": true, "appointment_create": false}', False),
    ('doctor', '{"ehr_write": true, "appointment_create": false}', False),
    ('nurse', '{"ehr_write": false, "appointment_create": true}', False),
    ('staff', '{"ehr_write": true, "appointment_create": false}', False),
    ('patient', '{"ehr_write": true, "appointment_create": false}', False)
]

import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

@router.post("/subscribe", response_model=SubscriptionResponse)
async def subscribe(
    tenant_data: TenantCreate,
    subscription: SubscriptionCreate,
    db: AsyncSession = Depends(get_db),
):
    # Validate plan exists
    print(tenant_data)
    print(subscription)
    plan = await db.execute(select(Plan).where(Plan.id == subscription.plan_id))
    plan = plan.scalar()

    if not plan:
        raise HTTPException(status_code=400, detail="Invalid plan")

    amount = plan.price

    # Payment Gateway Integration
    try:
        order = await razorpay_service.create_order(amount=amount)
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Payment processing failed: {str(e)}"
        )

    # Don't start a transaction here - FastAPI/SQLAlchemy already manages one
    try:

        new_tenant = Tenant(
            name=tenant_data.name,
            subdomain=tenant_data.subdomain,
            plan_id=subscription.plan_id,
            subscription_id=order["id"],
            payment_status="pending",
            next_billing_date=None,
        )
        db.add(new_tenant)
        await db.commit()  # Commit immediately to make tenant visible

        # roles = (await db.execute(select(Role))).scalars().all()

        # response = await vault.register_tenant(str(new_tenant.id), roles)
        schema_name = f"tenant_{new_tenant.id}"

        # Create tenant schema
        await db.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}"))

        # Get a connection from the async session
        tenant_schema.set(schema_name)
        conn = await db.connection()
        await conn.run_sync(
            lambda sync_conn: TenantAwareBase.metadata.create_all(bind=sync_conn)
        )

        
        for role_data in DEFAULT_ROLES:
            role = Role(
                name=role_data[0],
                permissions=json.loads(role_data[1]),
                is_custom=role_data[2]
            )
            db.add(role)
        await db.flush()

        admin_password = "test@12346789"
        hashed_password = get_password_hash(admin_password)
        clinic_admin = (await db.execute(select(Role).where(Role.name == "clinic_admin"))).scalar()
        if not clinic_admin:
            raise HTTPException(status_code=500, detail="clinic_admin role not found")
        new_user = User(
            email=tenant_data.email,
            password_hash=hashed_password,
            role=clinic_admin,
            tenant_id=new_tenant.id,
            is_active=True,
        )
        db.add(new_user)
        await db.flush()

        await db.commit()
        

    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating tenant tables: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while creating the tenant: {str(e)}"
        )

    return SubscriptionResponse(
        id=new_tenant.id,
        tenant_id=new_tenant.id,
        plan_id=new_tenant.plan_id,
        payment_status=new_tenant.payment_status,
        amount = amount,
        subscription_id=new_tenant.subscription_id,
        next_billing_date=new_tenant.next_billing_date
    )

@router.post("/webhook/razorpay")
async def razorpay_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    payload = await request.json()
    print("Received Payload:", payload)

    # Extract necessary fields
    razorpay_order_id = payload.get("razorpay_order_id")
    razorpay_payment_id = payload.get("razorpay_payment_id")
    razorpay_signature = payload.get("razorpay_signature")

    if not all([razorpay_order_id, razorpay_payment_id, razorpay_signature]):
        raise HTTPException(status_code=400, detail="Missing required Razorpay fields")

    # Verify payment signature
    try:
        razorpay_service.verify_payment(razorpay_order_id, razorpay_payment_id, razorpay_signature)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid Razorpay signature")

    # Fetch the tenant using the subscription ID (order ID)
    result = await db.execute(select(Tenant).where(Tenant.subscription_id == razorpay_order_id))
    tenant = result.scalars().first()

    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Fetch the user associated with the tenant (assuming the admin is the payer)
    user_result = await db.execute(select(User).where(User.tenant_id == tenant.id).order_by(User.id))
    user = user_result.scalars().first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found for tenant")

    # Fetch payment details from Razorpay API
    try:
        payment_details = await razorpay_service.get_payment_details(razorpay_payment_id)
        amount = payment_details["amount"] // 100  # Convert paise to INR
        currency = payment_details["currency"]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch payment details: {str(e)}")

    # Update Tenant Subscription Status
    tenant.payment_status = "active"
    tenant.next_billing_date = datetime.utcnow() + timedelta(days=30)
    await db.commit()

    # Create Transaction Entry
    transaction = Transaction(
        tenant_id=tenant.id,
        payment_gateway="Razorpay",
        transaction_id=razorpay_payment_id,
        amount=amount,  # Assigning amount
        currency=currency,
        status="completed",
    )
    db.add(transaction)
    await db.commit()

    return {"status": "success"}


@router.post("/renew", response_model=SubscriptionResponse)
async def renew_subscription(
    tenant_id: int,
    subscription: SubscriptionCreate,
    db: AsyncSession = Depends(get_db),
):
    tenant = await db.execute(select(Tenant).filter_by(id=tenant_id))
    tenant = tenant.scalars().first()

    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    order = razorpay_service.create_order(amount=1000)  # Example amount

    tenant.payment_status = "pending"
    await db.commit()

    return {"order_id": order["id"], "amount": 1000, "currency": "INR"}

