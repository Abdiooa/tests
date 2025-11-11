"""Database configuration and connection setup"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import NullPool
import logging

logger = logging.getLogger(__name__)

# Database configuration
DATABASE_URL = "postgresql+asyncpg://postgres:dadinos@localhost:5432/test_db"

# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL query logging
    poolclass=NullPool,  # Use NullPool to avoid connection pooling issues
)

# Create async session factory (compatible with SQLAlchemy 1.4 and 2.0)
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Create declarative base for ORM models
Base = declarative_base()


async def get_db():
    """Dependency to get database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_database():
    """Initialize database tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created successfully")


async def close_database():
    """Close database connections"""
    await engine.dispose()
    logger.info("Database connections closed")

