from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from page_crafter.shared.settings.app import get_settings


def build_engine():
    """Create a SQLAlchemy engine using the configured database URL."""
    settings = get_settings()
    return create_engine(settings.database_url, pool_pre_ping=True)


engine = build_engine()
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)


def get_session() -> Generator[Session]:
    """Yield a database session and guarantee cleanup after request handling."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
