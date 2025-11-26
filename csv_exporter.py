"""CSV export service for XDR records grouped by 1-minute intervals"""
import csv
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from pathlib import Path
import logging
from zoneinfo import ZoneInfo
import asyncio
from ftplib import FTP

# Get records directory from environment variable or use default
DEFAULT_RECORDS_DIR = os.getenv("RECORDS_DIR", "./records")

from models import CdrRecord, PdrRecord, SdrRecord, EdrRecord, TopUpRecord
from database import AsyncSessionLocal
from db_models import (
    CdrRecordDB, PdrRecordDB, SdrRecordDB, EdrRecordDB, TopUpRecordDB
)
from sqlalchemy import select, and_

logger = logging.getLogger(__name__)


class CsvExporter:
    """Exports XDR records to CSV files grouped by 1-minute intervals"""
    
    def __init__(self, records_dir: str = "./records", buffer_seconds: int = 10):
        """
        Initialize CSV exporter
        
        Args:
            records_dir: Directory to store CSV files
            buffer_seconds: Buffer time in seconds to ensure no records are missed
        """
        self.records_dir = Path(records_dir)
        self.buffer_seconds = buffer_seconds
        self.nairobi_tz = ZoneInfo("Africa/Nairobi")
        self.exported_intervals: set = set()  # Track exported intervals to avoid duplicates
        # Running totals of exported records
        self.total_exported_records: int = 0
        self.total_exported_by_type: dict[str, int] = {
            "cdr": 0,
            "pdr": 0,
            "sdr": 0,
            "edr": 0,
            "topups": 0,
        }
        # Track last exported timestamp per record type to ensure no duplicates
        # Only export records newer than this timestamp
        self.last_exported_timestamp: dict[str, Optional[datetime]] = {
            "cdr": None,
            "pdr": None,
            "sdr": None,
            "edr": None,
            "topups": None,
        }
        
        # FTP configuration from environment variables
        self.ftp_enabled = os.getenv("FTP_ENABLED", "false").lower() == "true"
        self.ftp_host = os.getenv("FTP_HOST", "localhost")
        self.ftp_port = int(os.getenv("FTP_PORT", "21"))
        self.ftp_user = os.getenv("FTP_USER", "aoo")
        self.ftp_password = os.getenv("FTP_PASSWORD", "0517")
        self.ftp_remote_dir = os.getenv("FTP_REMOTE_DIR", "/records")
        
        # Create records directory if it doesn't exist
        self.records_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"CSV exporter initialized. Records directory: {self.records_dir.absolute()}")
        if self.ftp_enabled:
            logger.info(f"FTP upload enabled: {self.ftp_user}@{self.ftp_host}:{self.ftp_port}{self.ftp_remote_dir}")
        else:
            logger.info("FTP upload disabled")
    
    def _format_timestamp_for_filename(self, dt: datetime) -> str:
        """Format datetime for filename: YYYYMMDDTHHMMSS"""
        # Ensure timezone-aware datetime
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=self.nairobi_tz)
        else:
            dt = dt.astimezone(self.nairobi_tz)
        
        # Format as YYYYMMDDTHHMMSS
        return dt.strftime("%Y%m%dT%H%M%S")
    
    def _get_csv_filename(self, record_type: str, since: datetime, until: datetime) -> str:
        """Generate CSV filename: {type}_sincetimestamp_untilsincetimestamp.csv"""
        since_str = self._format_timestamp_for_filename(since)
        until_str = self._format_timestamp_for_filename(until)
        
        # Normalize record type for filename
        type_map = {
            "cdr": "cdr",
            "pdr": "pdr",
            "sdr": "sdr",
            "edr": "edr",
            "topups": "topups"
        }
        normalized_type = type_map.get(record_type.lower(), record_type.lower())
        
        return f"{normalized_type}_{since_str}-{until_str}.csv"
    
    def _db_to_pydantic_model(self, db_obj, pydantic_class):
        """Convert SQLAlchemy model to Pydantic model"""
        data = {}
        for column in db_obj.__table__.columns:
            value = getattr(db_obj, column.name)
            # Attach timezone to datetime fields (database stores as timezone-naive)
            if isinstance(value, datetime) and value.tzinfo is None:
                value = value.replace(tzinfo=self.nairobi_tz)
            data[column.name] = value
        return pydantic_class(**data)
    
    async def _get_records_for_interval(
        self,
        record_type: str,
        since: datetime,
        until: datetime,
        db_model_class,
        actual_since: Optional[datetime] = None,
        actual_until: Optional[datetime] = None
    ) -> List:
        """
        Get records for a specific time interval from database
        
        Args:
            record_type: Type of record (for logging)
            since: Query start timestamp (inclusive) - can include buffer
            until: Query end timestamp (exclusive) - can include buffer
            db_model_class: SQLAlchemy model class
            actual_since: Actual interval start (inclusive) - for filtering duplicates. If None, uses since.
            actual_until: Actual interval end (exclusive) - for filtering duplicates. If None, uses until.
        
        Returns:
            List of records within the actual interval boundaries (filtered from query results)
        """
        async with AsyncSessionLocal() as session:
            try:
                # Convert timezone-aware datetimes to timezone-naive for database comparison
                since_db = since.astimezone(self.nairobi_tz).replace(tzinfo=None) if since.tzinfo else since
                until_db = until.astimezone(self.nairobi_tz).replace(tzinfo=None) if until.tzinfo else until
                
                # Query records in the time range (with buffer to catch edge cases)
                query = select(db_model_class).where(
                    and_(
                        db_model_class.timestamp >= since_db,
                        db_model_class.timestamp < until_db
                    )
                ).order_by(db_model_class.timestamp.asc())
                
                result = await session.execute(query)
                db_records = result.scalars().all()
                
                # Convert to Pydantic models
                pydantic_class_map = {
                    CdrRecordDB: CdrRecord,
                    PdrRecordDB: PdrRecord,
                    SdrRecordDB: SdrRecord,
                    EdrRecordDB: EdrRecord,
                    TopUpRecordDB: TopUpRecord
                }
                pydantic_class = pydantic_class_map.get(db_model_class)
                
                if not pydantic_class:
                    return []
                
                # Convert all records to Pydantic models
                all_records = [self._db_to_pydantic_model(r, pydantic_class) for r in db_records]
                
                # Filter out records that have already been exported (ensure only new records)
                normalized_type = record_type.lower()
                last_exported = self.last_exported_timestamp.get(normalized_type)
                if last_exported is not None:
                    # Ensure timezone-aware for comparison
                    if last_exported.tzinfo is None:
                        last_exported = last_exported.replace(tzinfo=self.nairobi_tz)
                    else:
                        last_exported = last_exported.astimezone(self.nairobi_tz)
                    
                    # Filter to only include records newer than last exported timestamp
                    new_records = []
                    for record in all_records:
                        record_timestamp = record.timestamp
                        if record_timestamp.tzinfo is None:
                            record_timestamp = record_timestamp.replace(tzinfo=self.nairobi_tz)
                        else:
                            record_timestamp = record_timestamp.astimezone(self.nairobi_tz)
                        
                        # Only include records strictly newer than last exported
                        if record_timestamp > last_exported:
                            new_records.append(record)
                    
                    if len(all_records) != len(new_records):
                        filtered_count = len(all_records) - len(new_records)
                        logger.info(
                            f"Filtered {record_type} records: {len(all_records)} queried, "
                            f"{filtered_count} already exported (skipped), "
                            f"{len(new_records)} new records to export. "
                            f"Last exported timestamp: {last_exported}"
                        )
                    all_records = new_records
                
                # Filter to actual interval boundaries to prevent duplicates
                if actual_since is not None or actual_until is not None:
                    actual_since_filter = actual_since if actual_since is not None else since
                    actual_until_filter = actual_until if actual_until is not None else until
                    
                    # Ensure timezone-aware for comparison
                    if actual_since_filter.tzinfo is None:
                        actual_since_filter = actual_since_filter.replace(tzinfo=self.nairobi_tz)
                    else:
                        actual_since_filter = actual_since_filter.astimezone(self.nairobi_tz)
                    
                    if actual_until_filter.tzinfo is None:
                        actual_until_filter = actual_until_filter.replace(tzinfo=self.nairobi_tz)
                    else:
                        actual_until_filter = actual_until_filter.astimezone(self.nairobi_tz)
                    
                    filtered_records = []
                    for record in all_records:
                        # Get timestamp from record (should be timezone-aware after conversion)
                        record_timestamp = record.timestamp
                        if record_timestamp.tzinfo is None:
                            record_timestamp = record_timestamp.replace(tzinfo=self.nairobi_tz)
                        else:
                            record_timestamp = record_timestamp.astimezone(self.nairobi_tz)
                        
                        # Include only records within actual interval boundaries
                        if record_timestamp >= actual_since_filter and record_timestamp < actual_until_filter:
                            filtered_records.append(record)
                    
                    if len(all_records) != len(filtered_records):
                        logger.debug(
                            f"Filtered {record_type} records: {len(all_records)} queried (with buffer), "
                            f"{len(filtered_records)} within actual interval boundaries"
                        )
                    
                    return filtered_records
                
                return all_records
            except Exception as e:
                logger.error(f"Error fetching {record_type} records: {e}")
                return []
    
    def _get_csv_headers(self, record_type: str, sample_record) -> List[str]:
        """Get CSV headers from a sample record"""
        if sample_record is None:
            return []
        
        # Get all fields from the Pydantic model
        model_dict = sample_record.model_dump(mode="json")
        return list(model_dict.keys())
    
    async def _write_csv_file(
        self,
        record_type: str,
        records: List,
        filename: str
    ) -> bool:
        """Write records to CSV file"""
        if not records:
            logger.debug(f"No {record_type} records to write for {filename}")
            return False
        
        filepath = self.records_dir / filename
        
        try:
            records_written_count = 0
            # Get headers from first record
            headers = self._get_csv_headers(record_type, records[0])
            
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=headers)
                writer.writeheader()
                
                for record in records:
                    # Convert record to dict, handling special types
                    record_dict = record.model_dump(mode="json")
                    
                    # Convert datetime objects to ISO format strings
                    for key, value in record_dict.items():
                        if isinstance(value, datetime):
                            record_dict[key] = value.isoformat()
                        elif value is None:
                            record_dict[key] = ""
                    
                    writer.writerow(record_dict)
                    records_written_count += 1
            
            logger.info(f"Exported {len(records)} {record_type} records to {filename}")
            
            # Update running totals
            normalized_type = record_type.lower()
            if normalized_type in self.total_exported_by_type:
                self.total_exported_by_type[normalized_type] += records_written_count
            self.total_exported_records += records_written_count
            logger.info(
                f"CSV export counters updated: +{records_written_count} {record_type} "
                f"(total {record_type}: {self.total_exported_by_type.get(normalized_type, 0)}, "
                f"grand total: {self.total_exported_records})"
            )
            
            # Upload to FTP if enabled
            ftp_success = True
            if self.ftp_enabled:
                ftp_success = await self._upload_to_ftp(filepath, filename)
            
            # Update last exported timestamp only if export was successful
            # Track the maximum timestamp from exported records
            if records and ftp_success:
                max_timestamp = None
                for record in records:
                    record_timestamp = record.timestamp
                    if record_timestamp.tzinfo is None:
                        record_timestamp = record_timestamp.replace(tzinfo=self.nairobi_tz)
                    else:
                        record_timestamp = record_timestamp.astimezone(self.nairobi_tz)
                    
                    if max_timestamp is None or record_timestamp > max_timestamp:
                        max_timestamp = record_timestamp
                
                if max_timestamp is not None:
                    # Update last exported timestamp to the maximum timestamp of exported records
                    old_timestamp = self.last_exported_timestamp.get(normalized_type)
                    self.last_exported_timestamp[normalized_type] = max_timestamp
                    if old_timestamp is None:
                        logger.debug(
                            f"Set initial last exported timestamp for {record_type}: {max_timestamp}"
                        )
                    else:
                        logger.debug(
                            f"Updated last exported timestamp for {record_type}: "
                            f"{old_timestamp} -> {max_timestamp}"
                        )
            
            return ftp_success if self.ftp_enabled else True
        except Exception as e:
            logger.error(f"Error writing CSV file {filename}: {e}")
            return False
    
    async def _upload_to_ftp(self, filepath: Path, filename: str, max_retries: int = 3):
        """
        Upload CSV file to FTP server using ftplib (Python 3.12 compatible)
        
        Args:
            filepath: Local file path
            filename: Filename to use on FTP server
            max_retries: Maximum number of retry attempts
        """
        if not self.ftp_enabled:
            return
        
        def _sync_ftp_upload():
            """Synchronous FTP upload function to be run in thread"""
            ftp = None
            try:
                # Connect to FTP server
                ftp = FTP()
                ftp.connect(self.ftp_host, self.ftp_port)
                ftp.login(self.ftp_user, self.ftp_password)
                
                # Change to remote directory
                if self.ftp_remote_dir and self.ftp_remote_dir != "/":
                    try:
                        ftp.cwd(self.ftp_remote_dir)
                    except Exception as e:
                        logger.warning(f"Could not change to FTP directory {self.ftp_remote_dir}: {e}. Using root.")
                
                # Upload file
                with open(filepath, 'rb') as f:
                    ftp.storbinary(f'STOR {filename}', f)
                
                logger.info(f"Successfully uploaded {filename} to FTP server")
                return True
            except Exception as e:
                logger.error(f"FTP upload error: {e}")
                raise
            finally:
                if ftp:
                    try:
                        ftp.quit()
                    except:
                        try:
                            ftp.close()
                        except:
                            pass
        
        for attempt in range(max_retries):
            try:
                # Run synchronous FTP operations in thread pool
                await asyncio.to_thread(_sync_ftp_upload)
                return True
                    
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"FTP upload attempt {attempt + 1}/{max_retries} failed for {filename}: {e}. Retrying...")
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                else:
                    logger.error(f"Failed to upload {filename} to FTP server after {max_retries} attempts: {e}")
                    # Return False instead of raising - FTP failure shouldn't stop CSV export
                    # but we need to track it for timestamp updates
                    return False
    
    async def export_interval(
        self,
        since: datetime,
        until: datetime,
        record_types: Optional[List[str]] = None,
        filename_since: Optional[datetime] = None,
        filename_until: Optional[datetime] = None
    ) -> Dict[str, bool]:
        """
        Export records for a specific time interval to CSV files
        
        Args:
            since: Start timestamp (inclusive) - can include buffer for querying
            until: End timestamp (exclusive) - can include buffer for querying
            record_types: List of record types to export. If None, exports all types.
            filename_since: Start timestamp for filename (without buffer). If None, calculated from since.
            filename_until: End timestamp for filename (without buffer). If None, calculated from since.
        
        Returns:
            Dictionary mapping record types to success status
        """
        if record_types is None:
            record_types = ["cdr", "pdr", "sdr", "edr", "topups"]
        
        # Calculate the actual 1-minute interval for filename (without buffer)
        if filename_since is None or filename_until is None:
            # Round to nearest minute boundaries
            calc_since = since.replace(second=0, microsecond=0)
            if calc_since.tzinfo is None:
                calc_since = calc_since.replace(tzinfo=self.nairobi_tz)
            else:
                calc_since = calc_since.astimezone(self.nairobi_tz)
            
            filename_since = filename_since if filename_since is not None else calc_since
            filename_until = filename_until if filename_until is not None else (calc_since + timedelta(minutes=1))
        
        # Map record types to database models
        db_model_map = {
            "cdr": CdrRecordDB,
            "pdr": PdrRecordDB,
            "sdr": SdrRecordDB,
            "edr": EdrRecordDB,
            "topups": TopUpRecordDB
        }
        
        results = {}
        interval_counts: dict[str, int] = {rt: 0 for rt in ["cdr", "pdr", "sdr", "edr", "topups"]}
        
        for record_type in record_types:
            db_model_class = db_model_map.get(record_type)
            if not db_model_class:
                logger.warning(f"Unknown record type: {record_type}")
                results[record_type] = False
                continue
            
            # Get records for this interval (using buffer range for query, but filter to actual boundaries)
            records = await self._get_records_for_interval(
                record_type, since, until, db_model_class,
                actual_since=filename_since, actual_until=filename_until
            )
            
            if records:
                # Generate filename using actual interval boundaries (without buffer)
                filename = self._get_csv_filename(record_type, filename_since, filename_until)
                
                # Check if file already exists (avoid overwriting)
                filepath = self.records_dir / filename
                if filepath.exists():
                    logger.debug(f"CSV file {filename} already exists, skipping")
                    results[record_type] = True
                    interval_counts[record_type] = 0
                    continue
                
                # Write CSV file
                success = await self._write_csv_file(record_type, records, filename)
                results[record_type] = success
                interval_counts[record_type] = len(records) if success else 0
            else:
                logger.debug(f"No {record_type} records found for interval {since} to {until}")
                results[record_type] = True  # No records is not an error
                interval_counts[record_type] = 0
        
        # Log interval summary and running totals
        interval_total = sum(interval_counts.values())
        logger.info(
            "CSV export summary for interval: "
            f"{filename_since} to {filename_until} | "
            f"cdr={interval_counts['cdr']}, "
            f"pdr={interval_counts['pdr']}, "
            f"sdr={interval_counts['sdr']}, "
            f"edr={interval_counts['edr']}, "
            f"topups={interval_counts['topups']} | "
            f"interval total={interval_total} | "
            f"running grand total={self.total_exported_records}"
        )
        
        return results
    
    def _get_interval_key(self, since: datetime, until: datetime) -> str:
        """Generate a unique key for an interval"""
        since_str = self._format_timestamp_for_filename(since)
        until_str = self._format_timestamp_for_filename(until)
        return f"{since_str}-{until_str}"
    
    async def export_last_minute(self) -> Dict[str, bool]:
        """
        Export records from the last completed minute to CSV files.
        Only exports if the interval hasn't been exported before.
        
        Returns:
            Dictionary mapping record types to success status
        """
        now = datetime.now(self.nairobi_tz)
        
        # Calculate the last completed minute
        # Round down current time to nearest minute, then go back 1 minute
        # Example: if now is 10:05:30, last completed minute is 10:04:00 to 10:05:00
        current_minute = now.replace(second=0, microsecond=0)
        until = current_minute  # End of last completed minute
        since = until - timedelta(minutes=1)  # Start of last completed minute
        
        # Check if this interval has already been exported
        interval_key = self._get_interval_key(since, until)
        if interval_key in self.exported_intervals:
            logger.debug(f"Interval {interval_key} already exported, skipping")
            return {rt: True for rt in ["cdr", "pdr", "sdr", "edr", "topups"]}
        
        # Add buffer to ensure we don't miss any records
        # We'll query from (since - buffer) to (until + buffer)
        since_with_buffer = since - timedelta(seconds=self.buffer_seconds)
        until_with_buffer = until + timedelta(seconds=self.buffer_seconds)
        
        logger.info(f"Exporting records for interval: {since} to {until} (with buffer: {since_with_buffer} to {until_with_buffer})")
        
        # Export using the actual interval boundaries for filename, but query with buffer
        results = await self.export_interval(
            since_with_buffer, 
            until_with_buffer, 
            filename_since=since, 
            filename_until=until
        )
        
        # Mark this interval as exported if at least one type succeeded
        if any(results.values()):
            self.exported_intervals.add(interval_key)
            logger.info(f"Marked interval {interval_key} as exported")
        
        return results
    
    async def export_all_pending_intervals(self) -> Dict[str, int]:
        """
        Export all pending 1-minute intervals that haven't been exported yet.
        This is useful for catching up on missed exports.
        
        Returns:
            Dictionary with count of intervals exported per record type
        """
        async with AsyncSessionLocal() as session:
            try:
                # Get the earliest and latest timestamps across all record types
                from sqlalchemy import func
                
                earliest_cdr = await session.execute(
                    select(func.min(CdrRecordDB.timestamp))
                )
                earliest_pdr = await session.execute(
                    select(func.min(PdrRecordDB.timestamp))
                )
                earliest_sdr = await session.execute(
                    select(func.min(SdrRecordDB.timestamp))
                )
                earliest_edr = await session.execute(
                    select(func.min(EdrRecordDB.timestamp))
                )
                earliest_topup = await session.execute(
                    select(func.min(TopUpRecordDB.timestamp))
                )
                
                # Find the overall earliest timestamp
                timestamps = [
                    earliest_cdr.scalar(),
                    earliest_pdr.scalar(),
                    earliest_sdr.scalar(),
                    earliest_edr.scalar(),
                    earliest_topup.scalar()
                ]
                timestamps = [t for t in timestamps if t is not None]
                
                if not timestamps:
                    logger.info("No records found in database")
                    return {}
                
                earliest = min(timestamps)
                if earliest.tzinfo is None:
                    earliest = earliest.replace(tzinfo=self.nairobi_tz)
                else:
                    earliest = earliest.astimezone(self.nairobi_tz)
                
                # Round down to nearest minute
                earliest = earliest.replace(second=0, microsecond=0)
                
                # Get current time and round down to nearest minute
                now = datetime.now(self.nairobi_tz).replace(second=0, microsecond=0)
                
                # Export each 1-minute interval
                current = earliest
                interval_count = 0
                
                while current < now:
                    next_minute = current + timedelta(minutes=1)
                    since_with_buffer = current - timedelta(seconds=self.buffer_seconds)
                    until_with_buffer = next_minute + timedelta(seconds=self.buffer_seconds)
                    
                    # Pass actual interval boundaries to prevent duplicates
                    await self.export_interval(
                        since_with_buffer, 
                        until_with_buffer,
                        filename_since=current,
                        filename_until=next_minute
                    )
                    interval_count += 1
                    current = next_minute
                
                logger.info(f"Exported {interval_count} intervals")
                return {"intervals_exported": interval_count}
            except Exception as e:
                logger.error(f"Error exporting pending intervals: {e}")
                return {}

