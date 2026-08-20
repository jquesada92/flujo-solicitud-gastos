from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from app.core.config import get_settings
from app.core.database import Base
import app.models.classification  # noqa: F401
import app.models.closure  # noqa: F401
import app.models.entities  # noqa: F401
import app.models.iam  # noqa: F401

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

settings = get_settings()
database_url = settings.database_url
if database_url.startswith('postgresql://'):
    database_url = database_url.replace('postgresql://', 'postgresql+psycopg://', 1)

is_postgresql = database_url.startswith('postgresql+')
database_schema = settings.database_schema if is_postgresql else None
config.set_main_option('sqlalchemy.url', database_url)
config.attributes['database_schema'] = database_schema
target_metadata = Base.metadata


def include_name(name, type_, parent_names):
    """Restrict Alembic discovery to the configured application schema."""
    if not is_postgresql:
        return True
    if type_ == 'schema':
        return name in {None, database_schema}
    schema_name = parent_names.get('schema_name') if parent_names else None
    return schema_name in {None, database_schema}


def run_migrations_offline() -> None:
    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={'paramstyle': 'named'},
        compare_type=True,
        include_schemas=is_postgresql,
        include_name=include_name,
        version_table_schema=database_schema,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connect_args: dict[str, object] = {}
    if is_postgresql and database_schema:
        # Configure the PostgreSQL session before SQLAlchemy/Alembic starts its
        # migration transaction. This also makes unqualified migration SQL land
        # in the application schema instead of public.
        connect_args['options'] = f'-csearch_path={database_schema}'

    connectable = create_engine(
        database_url,
        poolclass=pool.NullPool,
        connect_args=connect_args,
    )

    with connectable.connect() as connection:
        if is_postgresql and database_schema:
            quoted_schema = connection.dialect.identifier_preparer.quote(database_schema)

            # CREATE SCHEMA starts SQLAlchemy's implicit transaction. Commit the
            # setup explicitly before handing the connection to Alembic; leaving
            # an external transaction open here causes Alembic's DDL to be rolled
            # back when the connection closes even though `upgrade head` exits 0.
            connection.exec_driver_sql(f'CREATE SCHEMA IF NOT EXISTS {quoted_schema}')
            connection.commit()

            # search_path is already set through libpq `options` above. Tell
            # SQLAlchemy which schema should be considered the default for
            # reflection/autogeneration without opening another transaction.
            connection.dialect.default_schema_name = database_schema

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            include_schemas=is_postgresql,
            include_name=include_name,
            version_table_schema=database_schema,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
