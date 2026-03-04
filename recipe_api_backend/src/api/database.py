"""
Database configuration and session management.

Flow: DatabaseConnectionFlow
Contract:
  - Input: Environment variables POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB, POSTGRES_PORT, POSTGRES_HOST
  - Output: SQLAlchemy engine and session factory
  - Side effects: Opens DB connections on first use
  - Errors: Raises on connection failure with context
"""
import logging
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

logger = logging.getLogger(__name__)

Base = declarative_base()

# Module-level singletons, initialized lazily
_engine = None
_SessionLocal = None


def _build_database_url() -> str:
    """Build the database URL from environment variables.

    Reads POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB, POSTGRES_PORT, POSTGRES_HOST
    and constructs a psycopg2 connection URL.

    Returns:
        A SQLAlchemy-compatible database URL string.
    """
    user = os.getenv("POSTGRES_USER", "appuser")
    password = os.getenv("POSTGRES_PASSWORD", "dbuser123")
    db_name = os.getenv("POSTGRES_DB", "myapp")
    port = os.getenv("POSTGRES_PORT", "5000")
    host = os.getenv("POSTGRES_HOST", "localhost")

    url = os.getenv("POSTGRES_URL", "")
    if url:
        # Ensure pg8000 driver prefix
        if "+" not in url.split("://")[0]:
            url = url.replace("postgresql://", "postgresql+pg8000://", 1)
        # If the POSTGRES_URL doesn't have credentials, inject them
        if "@" not in url.split("//", 1)[-1]:
            # URL has no auth info, rebuild with credentials
            url = f"postgresql+pg8000://{user}:{password}@{host}:{port}/{db_name}"
        return url

    return f"postgresql+pg8000://{user}:{password}@{host}:{port}/{db_name}"


def _get_engine():
    """Get or create the SQLAlchemy engine singleton.

    Returns:
        SQLAlchemy Engine instance.
    """
    global _engine
    if _engine is None:
        database_url = _build_database_url()
        # Log only the host portion for security
        safe_url = database_url.split("@")[-1] if "@" in database_url else database_url
        logger.info("Connecting to database at %s", safe_url)
        _engine = create_engine(
            database_url,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            echo=False,
            pool_reset_on_return="rollback",
        )
    return _engine


def _get_session_local():
    """Get or create the session factory singleton.

    Returns:
        SQLAlchemy sessionmaker instance.
    """
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_get_engine())
    return _SessionLocal


# PUBLIC_INTERFACE
def get_db():
    """
    FastAPI dependency that provides a database session.

    Yields a SQLAlchemy Session and ensures it is closed after the request.
    """
    session_factory = _get_session_local()
    db = session_factory()
    try:
        yield db
    finally:
        db.close()
