from sqlalchemy import MetaData, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import settings

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Same physical database as the anti-deforestación backend (one Supabase project,
# one plan) — its own Postgres schema keeps "parcels"/"analyses" from colliding
# with the anti-deforestación tables of the same name.
class Base(DeclarativeBase):
    metadata = MetaData(schema="corredores")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
