from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base, declared_attr
from contextvars import ContextVar
from sqlalchemy import event, text
from .config import settings

# Contextvar for dynamic tenant schemas
tenant_schema: ContextVar[str] = ContextVar("tenant_schema", default="public")

class RoutingSession(AsyncSession):
    def __init__(self, bind=None, **kwargs):
        if bind is None:
            bind = get_engine()
        super().__init__(bind=bind, **kwargs)

    async def connection(self, **kwargs):
        sync_conn = await super().connection(**kwargs)
        current_schema = tenant_schema.get()
        await sync_conn.execute(text(f"SET search_path TO {current_schema}"))
        return sync_conn

# Fixed engine configuration (removed invalid parameter)
engine = create_async_engine(
    str(settings.DATABASE_URL),
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_pre_ping=True,
    future=True,
)

# Rest of the file remains the same
AsyncSessionLocal = sessionmaker(
    class_=RoutingSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False
)

PublicBase = declarative_base()
TenantBase = declarative_base()

class TenantAwareBase(TenantBase):
    __abstract__ = True
    
    @declared_attr
    def __table_args__(cls):
        schema = tenant_schema.get()
        return {'schema': schema}
    
    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

def get_engine():
    return engine