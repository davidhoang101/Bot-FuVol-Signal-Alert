"""Database session management."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import settings
import os

# SQLite doesn't support async well, so we'll use sync for now
# For production, consider PostgreSQL with asyncpg
db_url = settings.DATABASE_URL
if db_url.startswith("sqlite:///"):
    # Ensure absolute path for SQLite
    db_path = db_url.replace("sqlite:///", "")
    if not os.path.isabs(db_path):
        # Make it relative to backend directory
        backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        db_path = os.path.join(backend_dir, db_path)
        # Ensure directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
    db_url = f"sqlite:///{db_path}"

engine = create_engine(
    db_url,
    connect_args={"check_same_thread": False} if "sqlite" in db_url else {},
    echo=settings.DEBUG
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def init_db():
    """Initialize database tables."""
    try:
        from app.db.models import Base
        Base.metadata.create_all(bind=engine)
        import logging
        logger = logging.getLogger(__name__)
        logger.info("Database tables initialized")
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error initializing database: {e}", exc_info=True)
        raise
