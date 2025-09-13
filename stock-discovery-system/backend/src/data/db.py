"""
Database utilities and connection management.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import Base
from ..config import settings
from ..utils.logging import logger


def init_db():
    """Initialize database with all tables."""
    try:
        engine = create_engine(settings.database_url)
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
        return engine
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


def get_session():
    """Get a database session."""
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()