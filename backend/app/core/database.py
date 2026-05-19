"""Database Connection and Session Management"""

from sqlalchemy import create_engine, event, pool
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session
from sqlalchemy.pool import QueuePool
from typing import Generator

from app.core.config import settings


# Create engine with connection pooling
engine = create_engine(
    settings.database_url,
    # Connection pooling
    poolclass=QueuePool,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_pre_ping=True,  # Test connections before using
    pool_recycle=3600,  # Recycle connections after 1 hour
    # Logging
    echo=settings.db_echo,
    # Other parameters
    connect_args={"connect_timeout": 10},
)

# Session factory
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=True,
)


class Base(DeclarativeBase):
    """Base class for all ORM models"""
    pass


def get_db() -> Generator[Session, None, None]:
    """
    Dependency for getting database session in FastAPI routes.

    Usage:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            items = db.query(Item).all()
            return items
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Initialize database (create all tables)"""
    Base.metadata.create_all(bind=engine)


def drop_db() -> None:
    """Drop all tables (WARNING: destructive)"""
    Base.metadata.drop_all(bind=engine)


# Event listeners for connection pooling
@event.listens_for(engine, "connect")
def receive_connect(dbapi_conn, connection_record):
    """Enable connection-level features"""
    # Enable PostGIS extensions
    cursor = dbapi_conn.cursor()
    try:
        cursor.execute("CREATE EXTENSION IF NOT EXISTS postgis")
        cursor.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
        dbapi_conn.commit()
    except Exception as e:
        dbapi_conn.rollback()
        print(f"Warning: Could not enable PostGIS extensions: {e}")
    finally:
        cursor.close()
