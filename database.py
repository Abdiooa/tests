"""Database configuration and connection setup"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy import text
import logging
import os
import asyncio

logger = logging.getLogger(__name__)

# Database configuration from environment variables with fallback defaults
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "dadinos")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "test_db")

# Construct DATABASE_URL (mask password in logs)
DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
DATABASE_URL_LOGGED = f"postgresql+asyncpg://{DB_USER}:***@{DB_HOST}:{DB_PORT}/{DB_NAME}"

logger.info(f"Database configuration: {DATABASE_URL_LOGGED}")

# Create async engine with connection retry settings
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL query logging
    poolclass=NullPool,  # Use NullPool to avoid connection pooling issues
    pool_pre_ping=True,  # Verify connections before using them
    connect_args={
        "server_settings": {
            "application_name": "xdr_records_api"
        }
    }
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


async def wait_for_postgres(max_retries=30, retry_delay=2):
    """Wait for PostgreSQL server to be ready"""
    import asyncpg
    
    for attempt in range(max_retries):
        try:
            conn = await asyncpg.connect(
                host=DB_HOST,
                port=int(DB_PORT),
                user=DB_USER,
                password=DB_PASSWORD,
                database='postgres',
                timeout=5
            )
            await conn.close()
            logger.info("PostgreSQL server is ready")
            return True
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"PostgreSQL connection attempt {attempt + 1}/{max_retries} failed: {e}. Retrying in {retry_delay}s...")
                await asyncio.sleep(retry_delay)
            else:
                logger.error(f"Failed to connect to PostgreSQL after {max_retries} attempts: {e}")
                raise
    return False


async def wait_for_database(max_retries=30, retry_delay=2):
    """Wait for target database to be ready with retry logic"""
    for attempt in range(max_retries):
        try:
            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            logger.info(f"Database '{DB_NAME}' connection successful")
            return True
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"Database '{DB_NAME}' connection attempt {attempt + 1}/{max_retries} failed: {e}. Retrying in {retry_delay}s...")
                await asyncio.sleep(retry_delay)
            else:
                logger.error(f"Failed to connect to database '{DB_NAME}' after {max_retries} attempts: {e}")
                raise
    return False


async def ensure_database_exists():
    """Ensure the database exists (created by init script, just verify)"""
    import asyncpg
    
    try:
        # Connect to postgres database to check if our database exists
        conn = await asyncpg.connect(
            host=DB_HOST,
            port=int(DB_PORT),
            user=DB_USER,
            password=DB_PASSWORD,
            database='postgres',
            timeout=5
        )
        
        try:
            # Check if database exists
            exists = await conn.fetchval(
                "SELECT 1 FROM pg_database WHERE datname = $1",
                DB_NAME
            )
            
            if exists:
                logger.info(f"Database '{DB_NAME}' exists")
            else:
                logger.warning(f"Database '{DB_NAME}' does not exist yet. It should be created by the init script.")
        finally:
            await conn.close()
    except Exception as e:
        logger.warning(f"Could not verify database exists: {e}. Assuming init script will handle it.")
        # Don't raise - the init script should handle this


async def init_database():
    """Initialize database tables"""
    try:
        # First, wait for PostgreSQL server to be ready
        logger.info("Waiting for PostgreSQL server to be ready...")
        await wait_for_postgres()
        
        # Ensure database exists (create if needed)
        logger.info(f"Ensuring database '{DB_NAME}' exists...")
        await ensure_database_exists()
        
        # Wait a bit for database to be fully ready
        await asyncio.sleep(2)
        
        # Wait for our specific database to be ready
        logger.info(f"Waiting for database '{DB_NAME}' to be ready...")
        await wait_for_database()
        
        # Create tables
        logger.info("Creating database tables...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise


async def close_database():
    """Close database connections"""
    await engine.dispose()
    logger.info("Database connections closed")

