#!/usr/bin/env python3
"""
Database cleanup script - clears all data without dropping tables.
Use this to clear data while keeping the table structure.
"""
import asyncio
import sys
from database import AsyncSessionLocal
from db_models import (
    CdrRecordDB, PdrRecordDB, SdrRecordDB, EdrRecordDB, TopUpRecordDB
)
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Clear all data from database tables"""
    try:
        logger.info("Starting database cleanup...")
        logger.info("This will DELETE all records but keep table structure")
        
        async with AsyncSessionLocal() as session:
            # Delete all records from each table
            logger.info("Deleting records from cdr_records...")
            await session.execute(CdrRecordDB.__table__.delete())
            
            logger.info("Deleting records from pdr_records...")
            await session.execute(PdrRecordDB.__table__.delete())
            
            logger.info("Deleting records from sdr_records...")
            await session.execute(SdrRecordDB.__table__.delete())
            
            logger.info("Deleting records from edr_records...")
            await session.execute(EdrRecordDB.__table__.delete())
            
            logger.info("Deleting records from topup_records...")
            await session.execute(TopUpRecordDB.__table__.delete())
            
            await session.commit()
        
        logger.info("✓ All records deleted successfully!")
        logger.info("Tables remain intact and ready for new data.")
        
        return 0
    except Exception as e:
        logger.error(f"✗ Error cleaning database: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

