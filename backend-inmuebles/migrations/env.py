from logging.config import fileConfig

from alembic import context
import sqlalchemy as sa
from sqlalchemy import engine_from_config, pool

from app import models  # noqa: F401  (registers models on Base.metadata)
from app.config import settings
from app.database import Base

config = context.config
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def include_object(object, name, type_, reflected, compare_to):
    # This schema only owns objects under "inmuebles" — never touch tables
    # belonging to the other modules' schemas.
    if type_ == "table" and getattr(object, "schema", None) != "inmuebles":
        return False
    return True


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        version_table_schema="inmuebles",
        include_schemas=True,
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        # The "inmuebles" schema must exist before Alembic can create its own
        # version table inside it (version_table_schema below).
        connection.execute(sa.text("CREATE SCHEMA IF NOT EXISTS inmuebles"))
        connection.commit()
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table_schema="inmuebles",
            include_schemas=True,
            include_object=include_object,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
