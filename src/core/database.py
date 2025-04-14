from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base, declared_attr
from contextvars import ContextVar
from sqlalchemy import text
from .config import settings
import logging

# Set up logging
logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Contextvar for dynamic tenant schemas
tenant_schema: ContextVar[str] = ContextVar("tenant_schema", default="public")

# Engine configuration
engine = create_async_engine(
    str(settings.DATABASE_URL),
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_pre_ping=True,
    future=True,
    echo=True,
)

class RoutingSession(AsyncSession):
    def __init__(self, **kwargs):
        logger.debug("Initializing RoutingSession")
        if 'bind' not in kwargs:
            kwargs['bind'] = engine
        super().__init__(**kwargs)
    
    async def connection(self, **kwargs):
        logger.debug("Getting connection from RoutingSession")
        conn = await super().connection(**kwargs)
        current_schema = tenant_schema.get()
        logger.debug(f"Setting search_path to: {current_schema}")
        await conn.execute(text(f"SET search_path TO {current_schema}"))
        
        # Verify
        result = await conn.execute(text("SHOW search_path"))
        actual_path = (await result.fetchone())[0]
        logger.debug(f"Verified search_path: {actual_path}")
        return conn

# Session factory
def get_sessionmaker():
    logger.debug("Creating sessionmaker")
    return sessionmaker(
        class_=RoutingSession,
        bind=engine,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False
    )

AsyncSessionLocal = get_sessionmaker()

# Base classes
PublicBase = declarative_base()
TenantBase = declarative_base()

class TenantAwareBase(TenantBase):
    __abstract__ = True
    
    @declared_attr
    def __table_args__(cls):
        return {}  # No schema here - handled by search_path
    
    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

# Utility function
def get_engine():
    return engine