from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()
DATABASE_URL = settings.database_url
if DATABASE_URL.startswith('postgresql://'):
    DATABASE_URL = DATABASE_URL.replace('postgresql://', 'postgresql+psycopg://', 1)

engine_options = {
    'pool_pre_ping': True,
    'pool_recycle': 300,
}
if DATABASE_URL.startswith('postgresql+psycopg://'):
    engine_options['connect_args'] = {
        'options': f'-csearch_path={settings.database_schema},public'
    }

engine = create_engine(DATABASE_URL, **engine_options)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Provide one SQLAlchemy session per request and always close it."""
    with SessionLocal() as db:
        yield db
