from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from core.models.public import Tenant

router = APIRouter()

@router.post("/tenant/{tenant_id}/subscribe")
async def subscribe_tenant(tenant_id: int, db: AsyncSession = Depends(get_db)):
    # Mark the tenant as active
    tenant = await db.execute(select(Tenant).filter_by(id=tenant_id))
    tenant = tenant.scalars().first()

    if tenant:
        tenant.is_active = True
        await db.commit()

        # Create schema for tenant
        await create_tenant_schema(tenant.id, db)

        return {"message": "Tenant subscribed successfully and schema created."}
    else:
        return {"message": "Tenant not found."}
