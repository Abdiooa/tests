from fastapi import FastAPI, Query, status
from fastapi.responses import JSONResponse, Response
from contextlib import asynccontextmanager
import asyncio
from datetime import datetime, timezone
from typing import Optional, List
from decimal import Decimal
import logging
from sqlalchemy import select, func, text
from zoneinfo import ZoneInfo

from models import (
    CdrRecord, PdrRecord, SdrRecord, EdrRecord, TopUpRecord
)
from generator import XdrRecordGenerator
from database import init_database, close_database, AsyncSessionLocal
from db_models import (
    CdrRecordDB, PdrRecordDB, SdrRecordDB, EdrRecordDB, TopUpRecordDB
)
from csv_exporter import CsvExporter

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Database storage
class RecordStorage:
    def __init__(self):
        import os
        self.generator = XdrRecordGenerator()
        self.generation_task: Optional[asyncio.Task] = None
        self.csv_export_task: Optional[asyncio.Task] = None
        records_dir = os.getenv("RECORDS_DIR", "./records")
        self.csv_exporter = CsvExporter(records_dir=records_dir, buffer_seconds=10)
        self.last_exported_minute: Optional[datetime] = None
    
    def _pydantic_to_db_model(self, pydantic_obj, db_model_class):
        """Convert Pydantic model to SQLAlchemy model"""
        data = pydantic_obj.model_dump()
        # Convert Decimal to string for proper database storage
        # Convert timezone-aware datetime to timezone-naive for database compatibility
        for key, value in data.items():
            if isinstance(value, Decimal):
                data[key] = value
            elif isinstance(value, datetime):
                # Strip timezone info if present (database uses TIMESTAMP WITHOUT TIME ZONE)
                data[key] = value.replace(tzinfo=None) if value.tzinfo is not None else value
        return db_model_class(**data)
    
    async def add_records(self, batch: dict):
        """Add a batch of records to database"""
        async with AsyncSessionLocal() as session:
            try:
                # Convert Pydantic models to SQLAlchemy models and add to session
                for cdr in batch["cdr"]:
                    session.add(self._pydantic_to_db_model(cdr, CdrRecordDB))
                
                for pdr in batch["pdr"]:
                    session.add(self._pydantic_to_db_model(pdr, PdrRecordDB))
                
                for sdr in batch["sdr"]:
                    session.add(self._pydantic_to_db_model(sdr, SdrRecordDB))
                
                for edr in batch["edr"]:
                    session.add(self._pydantic_to_db_model(edr, EdrRecordDB))
                
                for topup in batch["topups"]:
                    session.add(self._pydantic_to_db_model(topup, TopUpRecordDB))
                
                await session.commit()
                
                logger.info(
                    f"Added records to DB - CDR: {len(batch['cdr'])}, "
                    f"PDR: {len(batch['pdr'])}, SDR: {len(batch['sdr'])}, "
                    f"EDR: {len(batch['edr'])}, TopUps: {len(batch['topups'])}"
                )
            except Exception as e:
                await session.rollback()
                logger.error(f"Error adding records to database: {e}")
                raise
    
    async def get_records_since_until(self, since: Optional[datetime] = None, until: Optional[datetime] = None):
        """Get all records within a timestamp range from database"""
        async with AsyncSessionLocal() as session:
            try:
                # Convert timezone-aware datetimes to Africa/Nairobi local time (timezone-naive)
                # Database stores timestamps as timezone-naive representing Africa/Nairobi local time
                nairobi_tz = ZoneInfo("Africa/Nairobi")
                if since:
                    if since.tzinfo is not None:
                        # Convert to Africa/Nairobi timezone, then strip timezone for database comparison
                        since = since.astimezone(nairobi_tz).replace(tzinfo=None)
                    # If timezone-naive, assume it's already in Africa/Nairobi local time
                if until:
                    if until.tzinfo is not None:
                        # Convert to Africa/Nairobi timezone, then strip timezone for database comparison
                        until = until.astimezone(nairobi_tz).replace(tzinfo=None)
                    # If timezone-naive, assume it's already in Africa/Nairobi local time
                
                # Query each table with optional timestamp filters
                cdr_query = select(CdrRecordDB)
                pdr_query = select(PdrRecordDB)
                sdr_query = select(SdrRecordDB)
                edr_query = select(EdrRecordDB)
                topup_query = select(TopUpRecordDB)
                
                # Apply since filter (records at or after this timestamp)
                if since:
                    cdr_query = cdr_query.where(CdrRecordDB.timestamp >= since)
                    pdr_query = pdr_query.where(PdrRecordDB.timestamp >= since)
                    sdr_query = sdr_query.where(SdrRecordDB.timestamp >= since)
                    edr_query = edr_query.where(EdrRecordDB.timestamp >= since)
                    topup_query = topup_query.where(TopUpRecordDB.timestamp >= since)
                
                # Apply until filter (records at or before this timestamp)
                if until:
                    cdr_query = cdr_query.where(CdrRecordDB.timestamp <= until)
                    pdr_query = pdr_query.where(PdrRecordDB.timestamp <= until)
                    sdr_query = sdr_query.where(SdrRecordDB.timestamp <= until)
                    edr_query = edr_query.where(EdrRecordDB.timestamp <= until)
                    topup_query = topup_query.where(TopUpRecordDB.timestamp <= until)
                
                # Order by timestamp descending (most recent first)
                cdr_query = cdr_query.order_by(CdrRecordDB.timestamp.desc())
                pdr_query = pdr_query.order_by(PdrRecordDB.timestamp.desc())
                sdr_query = sdr_query.order_by(SdrRecordDB.timestamp.desc())
                edr_query = edr_query.order_by(EdrRecordDB.timestamp.desc())
                topup_query = topup_query.order_by(TopUpRecordDB.timestamp.desc())
                
                # Execute queries
                cdr_result = await session.execute(cdr_query)
                pdr_result = await session.execute(pdr_query)
                sdr_result = await session.execute(sdr_query)
                edr_result = await session.execute(edr_query)
                topup_result = await session.execute(topup_query)
                
                # Convert SQLAlchemy models back to Pydantic models
                cdr_records = [self._db_to_pydantic_model(r, CdrRecord) for r in cdr_result.scalars().all()]
                pdr_records = [self._db_to_pydantic_model(r, PdrRecord) for r in pdr_result.scalars().all()]
                sdr_records = [self._db_to_pydantic_model(r, SdrRecord) for r in sdr_result.scalars().all()]
                edr_records = [self._db_to_pydantic_model(r, EdrRecord) for r in edr_result.scalars().all()]
                topup_records = [self._db_to_pydantic_model(r, TopUpRecord) for r in topup_result.scalars().all()]
                
                return {
                    "cdr": cdr_records,
                    "pdr": pdr_records,
                    "sdr": sdr_records,
                    "edr": edr_records,
                    "topups": topup_records
                }
            except Exception as e:
                logger.error(f"Error fetching records from database: {e}")
                raise
    
    def _db_to_pydantic_model(self, db_obj, pydantic_class):
        """Convert SQLAlchemy model to Pydantic model"""
        # Assume all datetime values from database are in Africa/Nairobi timezone (UTC+3)
        nairobi_tz = ZoneInfo("Africa/Nairobi")
        data = {}
        for column in db_obj.__table__.columns:
            value = getattr(db_obj, column.name)
            # Attach timezone to datetime fields (database stores as timezone-naive)
            if isinstance(value, datetime) and value.tzinfo is None:
                value = value.replace(tzinfo=nairobi_tz)
            data[column.name] = value
        return pydantic_class(**data)
    
    async def get_total_count(self):
        """Get total number of records from database"""
        async with AsyncSessionLocal() as session:
            try:
                cdr_count = await session.execute(select(func.count()).select_from(CdrRecordDB))
                pdr_count = await session.execute(select(func.count()).select_from(PdrRecordDB))
                sdr_count = await session.execute(select(func.count()).select_from(SdrRecordDB))
                edr_count = await session.execute(select(func.count()).select_from(EdrRecordDB))
                topup_count = await session.execute(select(func.count()).select_from(TopUpRecordDB))
                
                return (
                    cdr_count.scalar() +
                    pdr_count.scalar() +
                    sdr_count.scalar() +
                    edr_count.scalar() +
                    topup_count.scalar()
                )
            except Exception as e:
                logger.error(f"Error getting total count from database: {e}")
                raise
    
    async def get_breakdown_counts(self):
        """Get count breakdown by record type"""
        async with AsyncSessionLocal() as session:
            try:
                cdr_count = await session.execute(select(func.count()).select_from(CdrRecordDB))
                pdr_count = await session.execute(select(func.count()).select_from(PdrRecordDB))
                sdr_count = await session.execute(select(func.count()).select_from(SdrRecordDB))
                edr_count = await session.execute(select(func.count()).select_from(EdrRecordDB))
                topup_count = await session.execute(select(func.count()).select_from(TopUpRecordDB))
                
                return {
                    "cdr": cdr_count.scalar(),
                    "pdr": pdr_count.scalar(),
                    "sdr": sdr_count.scalar(),
                    "edr": edr_count.scalar(),
                    "topups": topup_count.scalar()
                }
            except Exception as e:
                logger.error(f"Error getting breakdown counts from database: {e}")
                raise
    
    async def get_latest_timestamps(self):
        """Get latest timestamp for each record type"""
        async with AsyncSessionLocal() as session:
            try:
                cdr_latest = await session.execute(select(CdrRecordDB.timestamp).order_by(CdrRecordDB.timestamp.desc()).limit(1))
                pdr_latest = await session.execute(select(PdrRecordDB.timestamp).order_by(PdrRecordDB.timestamp.desc()).limit(1))
                sdr_latest = await session.execute(select(SdrRecordDB.timestamp).order_by(SdrRecordDB.timestamp.desc()).limit(1))
                edr_latest = await session.execute(select(EdrRecordDB.timestamp).order_by(EdrRecordDB.timestamp.desc()).limit(1))
                topup_latest = await session.execute(select(TopUpRecordDB.timestamp).order_by(TopUpRecordDB.timestamp.desc()).limit(1))
                
                return {
                    "cdr": cdr_latest.scalar(),
                    "pdr": pdr_latest.scalar(),
                    "sdr": sdr_latest.scalar(),
                    "edr": edr_latest.scalar(),
                    "topups": topup_latest.scalar()
                }
            except Exception as e:
                logger.error(f"Error getting latest timestamps from database: {e}")
                raise
    
    async def clear_all_records(self):
        """Clear all records from database"""
        async with AsyncSessionLocal() as session:
            try:
                await session.execute(CdrRecordDB.__table__.delete())
                await session.execute(PdrRecordDB.__table__.delete())
                await session.execute(SdrRecordDB.__table__.delete())
                await session.execute(EdrRecordDB.__table__.delete())
                await session.execute(TopUpRecordDB.__table__.delete())
                await session.commit()
                logger.info("All records cleared from database")
            except Exception as e:
                await session.rollback()
                logger.error(f"Error clearing records from database: {e}")
                raise
    
    async def start_generation(self):
        """Start the background record generation task"""
        async def generate_records():
            logger.info("Starting record generation task (every 15 seconds)")
            while True:
                try:
                    # Generate random number (20-50) of each record type every 15 seconds
                    batch = self.generator.generate_batch()
                    batch_size = sum(len(records) for records in batch.values())
                    await self.add_records(batch)
                    total = await self.get_total_count()
                    logger.info(
                        f"Generated batch: CDR={len(batch['cdr'])}, PDR={len(batch['pdr'])}, "
                        f"SDR={len(batch['sdr'])}, EDR={len(batch['edr'])}, TopUps={len(batch['topups'])} "
                        f"(Total in batch: {batch_size}, Total in database: {total})"
                    )
                except Exception as e:
                    logger.error(f"Error generating records: {e}")
                
                await asyncio.sleep(15)  # Wait 15 seconds
        
        self.generation_task = asyncio.create_task(generate_records())
    
    async def stop_generation(self):
        """Stop the background record generation task"""
        if self.generation_task:
            self.generation_task.cancel()
            try:
                await self.generation_task
            except asyncio.CancelledError:
                logger.info("Record generation task cancelled")
    
    async def start_csv_export(self):
        """Start the background CSV export task (runs every minute)"""
        async def export_csv_records():
            logger.info("Starting CSV export task (every 1 minute)")
            # Wait a bit before first export to ensure we have some records
            await asyncio.sleep(30)
            
            while True:
                try:
                    # Export the last completed minute
                    results = await self.csv_exporter.export_last_minute()
                    
                    # Log results
                    success_count = sum(1 for success in results.values() if success)
                    total_count = len(results)
                    logger.info(
                        f"CSV export completed: {success_count}/{total_count} record types exported successfully"
                    )
                    
                    # Log details for each type
                    for record_type, success in results.items():
                        if success:
                            logger.debug(f"  ✓ {record_type.upper()} exported successfully")
                        else:
                            logger.warning(f"  ✗ {record_type.upper()} export failed")
                    
                except Exception as e:
                    logger.error(f"Error in CSV export task: {e}")
                
                # Wait 60 seconds before next export
                await asyncio.sleep(60)
        
        self.csv_export_task = asyncio.create_task(export_csv_records())
    
    async def stop_csv_export(self):
        """Stop the background CSV export task"""
        if self.csv_export_task:
            self.csv_export_task.cancel()
            try:
                await self.csv_export_task
            except asyncio.CancelledError:
                logger.info("CSV export task cancelled")


# Initialize storage
storage = RecordStorage()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for FastAPI application"""
    # Startup: Initialize database and start background tasks
    logger.info("Starting Telecom XDR API Service")
    logger.info("Initializing database...")
    await init_database()
    logger.info("Database initialized successfully")
    await storage.start_generation()
    await storage.start_csv_export()
    yield
    # Shutdown: Stop background tasks and close database connections
    logger.info("Shutting down Telecom XDR API Service")
    await storage.stop_csv_export()
    await storage.stop_generation()
    await close_database()


# Initialize FastAPI app
app = FastAPI(
    title="Telecom XDR Records API",
    description="REST API simulating a telecom operator generating XDR records (CDR, PDR, SDR, EDR, TopUp)",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Telecom XDR Records API",
        "version": "1.0.0",
        "description": "Generates XDR records every 15 seconds and exports to CSV every 1 minute",
        "endpoints": {
            "/health": "Health check endpoint (supports GET and HEAD)",
            "/api/data": "Get all XDR records (supports 'since' and 'until' timestamp parameters)",
            "/api/stats": "Get statistics about stored records",
            "/api/export/csv": "Manually trigger CSV export for the last completed minute",
            "/api/data (DELETE)": "Clear all stored records"
        },
        "csv_export": {
            "enabled": True,
            "interval": "1 minute",
            "location": "./records",
            "format": "{type}_YYYYMMDDTHHMMSS-YYYYMMDDTHHMMSS.csv"
        }
    }


@app.get("/health")
@app.head("/health")
async def health_check():
    """
    Health check endpoint for monitoring and load balancers.
    Supports both GET (returns JSON) and HEAD (returns status only) requests.
    
    Checks:
    - Database connectivity
    - Background task status (record generation and CSV export)
    
    Returns:
    - 200 OK: All systems operational
    - 503 Service Unavailable: One or more components are unhealthy
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": {}
    }
    
    overall_healthy = True
    
    # Check database connectivity
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT 1"))
            result.scalar()
            health_status["checks"]["database"] = {
                "status": "healthy",
                "message": "Database connection successful"
            }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        health_status["checks"]["database"] = {
            "status": "unhealthy",
            "message": f"Database connection failed: {str(e)}"
        }
        overall_healthy = False
    
    # Check background tasks
    generation_running = storage.generation_task is not None and not storage.generation_task.done()
    csv_export_running = storage.csv_export_task is not None and not storage.csv_export_task.done()
    
    health_status["checks"]["background_tasks"] = {
        "status": "healthy" if (generation_running and csv_export_running) else "unhealthy",
        "details": {
            "record_generation": {
                "running": generation_running,
                "status": "running" if generation_running else "stopped"
            },
            "csv_export": {
                "running": csv_export_running,
                "status": "running" if csv_export_running else "stopped"
            }
        }
    }
    
    if not (generation_running and csv_export_running):
        overall_healthy = False
        health_status["status"] = "unhealthy"
    
    # Set overall status
    if not overall_healthy:
        health_status["status"] = "unhealthy"
    
    # Return appropriate status code
    status_code = status.HTTP_200_OK if overall_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
    
    return JSONResponse(
        content=health_status,
        status_code=status_code
    )


@app.get("/api/data")
async def get_data(
    since: Optional[datetime] = Query(
        None,
        description="ISO 8601 timestamp to fetch records at or after this time (inclusive). Accepts timezone-aware or timezone-naive timestamps. Timezone-aware timestamps are converted to Africa/Nairobi (UTC+3).",
        examples=["2025-11-05T10:44:17", "2025-11-05T10:44:17+03:00", "2025-11-05T07:44:17Z"]
    ),
    until: Optional[datetime] = Query(
        None,
        description="ISO 8601 timestamp to fetch records at or before this time (inclusive). Accepts timezone-aware or timezone-naive timestamps. Timezone-aware timestamps are converted to Africa/Nairobi (UTC+3).",
        examples=["2025-11-05T10:44:17", "2025-11-05T10:44:17+03:00", "2025-11-05T07:44:17Z"]
    )
):
    """
    Get all XDR records, optionally filtered by timestamp range.
    
    Returns a JSON object grouping arrays of each record type under "records":
    {
        "records": {
            "cdr": [...],
            "sdr": [...],
            "pdr": [...],
            "edr": [...],
            "topups": [...]
        }
    }
    
    Timestamp Format: ISO 8601 DateTime with timezone offset (Africa/Nairobi, UTC+3)
    Example: "timestamp": "2025-11-05T10:44:17.461620+03:00"
    
    Query Parameter Timestamps:
    - You can provide timestamps with or without timezone information
    - Timezone-aware timestamps (e.g., "+03:00", "Z", "+00:00") are automatically converted to Africa/Nairobi timezone
    - Timezone-naive timestamps are assumed to be in Africa/Nairobi local time
    
    - **since**: Optional ISO 8601 timestamp. If provided, returns records with timestamps >= since (inclusive).
    - **until**: Optional ISO 8601 timestamp. If provided, returns records with timestamps <= until (inclusive).
    - Use both parameters to get records within a specific time range.
    - Records with timestamps before 'since' will NOT be included.
    - Records with timestamps after 'until' will NOT be included.
    
    Examples:
    - Get all records: GET /api/data
    - Get records since a specific time: GET /api/data?since=2025-11-05T10:44:17
    - Get records in a range: GET /api/data?since=2025-11-05T10:00:00&until=2025-11-05T11:00:00
    - With timezone: GET /api/data?since=2025-11-05T07:44:17Z (UTC converted to Africa/Nairobi)
    """
    records = await storage.get_records_since_until(since, until)

    serialized_records = {
        record_type: [record.model_dump(mode="json") for record in record_list]
        for record_type, record_list in records.items()
    }

    # Return data grouped under a top-level "records" key to match the expected schema
    return {"records": serialized_records}


@app.get("/api/stats")
async def get_stats():
    """Get statistics about stored records"""
    total_count = await storage.get_total_count()
    breakdown = await storage.get_breakdown_counts()
    latest_timestamps = await storage.get_latest_timestamps()
    
    return {
        "timestamp": datetime.now(),
        "total_records": total_count,
        "breakdown": breakdown,
        "latest_records": latest_timestamps
    }


@app.delete("/api/data")
async def clear_data():
    """Clear all stored records (useful for testing)"""
    await storage.clear_all_records()
    
    return {
        "message": "All records cleared successfully from database",
        "timestamp": datetime.now()
    }


@app.post("/api/export/csv")
async def export_csv_manual():
    """
    Manually trigger CSV export for the last completed minute.
    This is useful for testing or manual exports.
    """
    try:
        results = await storage.csv_exporter.export_last_minute()
        
        success_count = sum(1 for success in results.values() if success)
        total_count = len(results)
        
        return {
            "message": f"CSV export completed: {success_count}/{total_count} record types exported",
            "results": results,
            "timestamp": datetime.now()
        }
    except Exception as e:
        logger.error(f"Error in manual CSV export: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "Failed to export CSV",
                "message": str(e),
                "timestamp": datetime.now()
            }
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

