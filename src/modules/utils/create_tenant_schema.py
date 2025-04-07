from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

async def create_tenant_schema(tenant_id: int, db: AsyncSession):
    # Construct schema name based on tenant ID or subdomain
    schema_name = f"tenant_{tenant_id}"

    # Check if schema already exists
    result = await db.execute(text(f"SELECT schema_name FROM information_schema.schemata WHERE schema_name = :schema_name"), {'schema_name': schema_name})
    schema = result.scalar()

    if not schema:
        # Create new schema for tenant
        await db.execute(text(f"CREATE SCHEMA {schema_name}"))
        await db.commit()

    # Set the schema in the context for further operations
    tenant_schema.set(schema_name)
