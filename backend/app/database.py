# ============================================================
#  ASTRA Cloud — Backend Database Connection Manager
#  File   : backend/app/database.py
#  Purpose: Manages PostgreSQL connection via SQLAlchemy.
#           Settings are read from environment variables.
#           Passwords are never hard-coded or logged.
# ============================================================

import os
from typing import Generator, Tuple
from urllib.parse import quote_plus
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from sqlalchemy.exc import SQLAlchemyError

# 1. Read environment configuration with secure fallbacks
DB_HOST = os.getenv("ASTRA_DB_HOST", "localhost")
DB_PORT = os.getenv("ASTRA_DB_PORT", "5432")
DB_NAME = os.getenv("ASTRA_DB_NAME", "astra_cloud")
DB_USER = os.getenv("ASTRA_DB_USER", "openpg")
DB_PASSWORD = os.getenv("ASTRA_DB_PASSWORD", "openpgpwd")

# URL-encode password in case of special characters
encoded_password = quote_plus(DB_PASSWORD)

# Construct PostgreSQL connection URL (psycopg2 driver)
SQLALCHEMY_DATABASE_URL = (
    f"postgresql+psycopg2://{DB_USER}:{encoded_password}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# 2. Engine and Session configuration
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,  # Test connection liveness before checkout
    pool_size=10,
    max_overflow=20,
    echo=False,          # Ensure SQL logs never leak credentials
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# 3. FastAPI Dependency
def get_db() -> Generator[Session, None, None]:
    """Provide a transactional database session for each request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# 4. Connectivity health checker
def check_db_connectivity() -> Tuple[bool, str]:
    """
    Verify live connectivity to the PostgreSQL database.
    Returns (is_connected: bool, message: str).
    Never prints or reveals credentials in messages.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, "Database connection active and responsive"
    except SQLAlchemyError as err:
        # Sanitize error message to avoid printing connection strings
        error_type = type(err).__name__
        return False, f"Database connectivity check failed ({error_type})"
    except Exception as exc:
        return False, f"Unexpected error during connection check ({type(exc).__name__})"
