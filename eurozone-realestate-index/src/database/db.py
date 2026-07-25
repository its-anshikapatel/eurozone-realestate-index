"""
Database engine and session management.

Provides a single shared SQLAlchemy engine (connection pool) and a
session factory. Other modules should import get_session() rather than
creating their own engines.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from config.settings import settings
from src.database.models import Base
from src.utils.logger import get_logger

logger = get_logger(__name__)

# pool_pre_ping avoids "stale connection" errors after Neon's serverless
# compute suspends due to inactivity (a real quirk of serverless Postgres).
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def init_db() -> None:
    """Create all tables defined in models.py if they don't already exist."""
    logger.info("Creating database tables if they do not exist...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables ready.")


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """
    Context-managed database session.

    Usage:
        with get_session() as session:
            session.add(some_object)
            session.commit()
    """
    session = SessionLocal()
    try:
        yield session
    except Exception:
        session.rollback()
        logger.exception("Database session rolled back due to an error.")
        raise
    finally:
        session.close()