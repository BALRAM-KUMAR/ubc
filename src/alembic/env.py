import sys
import os
from logging.config import fileConfig
from sqlalchemy import create_engine, pool, text
from alembic import context
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.database import TenantAwareBase, Base  # Import both TenantAwareBase and Base

config = context.config
fileConfig(config.config_file_name)

# Get tenant ID from environment variable or command line
tenant_id = 28  # Replace with dynamic tenant ID logic
if not tenant_id:
    raise ValueError("TENANT_ID environment variable must be set")

schema_name = f"tenant_{tenant_id}"

# Use only TenantAwareBase metadata for tenant-specific migrations
target_metadata = TenantAwareBase.metadata

def include_object(object, name, type_, reflected, compare_to):
    """
    Exclude public schema tables from tenant migrations.
    """
    if type_ == "table":
        logger.debug(f"Processing table: {object.schema}.{name} (type: {type_}, reflected: {reflected})")
        if object.schema == "public":
            logger.debug(f"Excluding public schema table: {name}")
            return False
    return True

def run_migrations_offline():
    """Run migrations in 'offline' mode."""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table_schema=schema_name,
        include_schemas=True,
        include_object=include_object  # Add this to filter out public schema tables
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    """Run migrations in 'online' mode."""
    connectable = create_engine(
        config.get_main_option("sqlalchemy.url"),
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        # Create tenant schema if not exists
        connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}"))
        
        # Set search path and configure context
        connection.execute(text(f"SET search_path TO {schema_name}"))
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table_schema=schema_name,
            include_schemas=True,
            compare_type=True,
            compare_server_default=True,
            include_object=include_object  # Add this to filter out public schema tables
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()





# import sys
# import os
# from logging.config import fileConfig
# from sqlalchemy import create_engine, pool
# from alembic import context

# # Add the src directory to the Python path
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# # Import your Base and models
# from core.database import Base, TenantAwareBase
# from core.models.public import Tenant, Transaction, Role, User, AuditLog

# # this is the Alembic Config object, which provides
# # access to the values within the .ini file in use.
# config = context.config

# # Interpret the config file for Python logging.
# fileConfig(config.config_file_name)

# # add your model's MetaData object here
# target_metadata = Base.metadata

# # After setting target_metadata
# print("Tables in metadata:", list(target_metadata.tables.keys()))
# print("Imported models:", [Tenant.__table__, Transaction.__table__])
# def run_migrations_offline():
#     """Run migrations in 'offline' mode."""
#     url = config.get_main_option("sqlalchemy.url")
#     context.configure(
#         url=url,
#         target_metadata=target_metadata,
#         literal_binds=True,
#         dialect_opts={"paramstyle": "named"},
#     )

#     with context.begin_transaction():
#         context.run_migrations()

# def run_migrations_online():
#     """Run migrations in 'online' mode."""
#     connectable = create_engine(
#         config.get_main_option("sqlalchemy.url"),
#         poolclass=pool.NullPool,
#     )

#     with connectable.connect() as connection:
#         context.configure(
#             connection=connection,
#             target_metadata=target_metadata
#         )

#         with context.begin_transaction():
#             context.run_migrations()

# if context.is_offline_mode():
#     run_migrations_offline()
# else:
#     run_migrations_online()