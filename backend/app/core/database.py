from sqlalchemy import MetaData, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import get_settings


settings = get_settings()
DATABASE_URL = settings.database_url
if DATABASE_URL.startswith('postgresql://'):
    DATABASE_URL = DATABASE_URL.replace('postgresql://', 'postgresql+psycopg://', 1)

IS_POSTGRESQL = DATABASE_URL.startswith('postgresql+')
APPLICATION_SCHEMA = settings.database_schema if IS_POSTGRESQL else None


class Base(DeclarativeBase):
    # PostgreSQL deployments qualify every ORM table with the configured
    # application schema. SQLite remains schema-less for unit tests.
    metadata = MetaData(schema=APPLICATION_SCHEMA)


connect_args: dict[str, object] = {}
if IS_POSTGRESQL:
    # Defense in depth: even unqualified SQL issued by dependencies resolves
    # only inside the application schema instead of falling back to public.
    connect_args['options'] = f'-csearch_path={settings.database_schema}'

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    connect_args=connect_args,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Provide one SQLAlchemy session per request and always close it."""
    with SessionLocal() as db:
        yield db
