import os
from collections.abc import Iterator

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

load_dotenv()


def database_url() -> str:
    return os.getenv(
        "TURNING_POINT_DATABASE_URL",
        "postgresql+psycopg2://postgres:password@localhost:5432/turning_point",
    )


class Base(DeclarativeBase):
    pass


SessionLocal = sessionmaker(bind=create_engine(database_url(), pool_pre_ping=True))


def get_db() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session
