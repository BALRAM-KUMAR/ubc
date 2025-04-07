from sqlalchemy import TypeDecorator, text, Integer
from core.config import settings

class TenantAwareForeignKey(TypeDecorator):
    impl = Integer
    
    def process_bind_param(self, value, dialect):
        # Validate tenant_id exists during insert/update
        print("jello",value)
        if value is not None:
            from sqlalchemy import create_engine
            engine = create_engine(str(settings.DATABASE_URL))
            with engine.connect() as conn:
                exists = conn.execute(
                    text("SELECT 1 FROM public.tenants WHERE id = :id"),
                    {"id": value}
                ).scalar()
                if not exists:
                    raise ValueError(f"Invalid tenant_id: {value}")
        return value