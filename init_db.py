#!/usr/bin/env python3
"""
Database initialization script.
Run this script to create all database tables.
"""
import asyncio
import sys
from database import init_database, engine
from db_models import (
    CdrRecordDB, PdrRecordDB, SdrRecordDB, EdrRecordDB, TopUpRecordDB
)
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Initialize the database (with cleanup)"""
    try:
        logger.info("Starting database initialization with cleanup...")
        logger.info(f"Database URL: {engine.url}")
        
        # Drop all existing tables first (clean slate)
        logger.info("Dropping existing tables if they exist...")
        from database import Base
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        logger.info("✓ Existing tables dropped")
        
        # Create all tables fresh
        logger.info("Creating fresh tables...")
        await init_database()
        
        logger.info("✓ Database tables created successfully!")
        logger.info("Tables created:")
        logger.info("  - cdr_records (Call Detail Records)")
        logger.info("  - pdr_records (Packet Data Records)")
        logger.info("  - sdr_records (Service Detail Records)")
        logger.info("  - edr_records (Event Detail Records)")
        logger.info("  - topup_records (Top-Up Records)")
        logger.info("")
        logger.info("⚠️  Note: All existing data has been cleared!")
        
        return 0
    except Exception as e:
        logger.error(f"✗ Error initializing database: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

