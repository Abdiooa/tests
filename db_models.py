"""SQLAlchemy database models for XDR records"""
from sqlalchemy import Column, String, Integer, DateTime, Boolean, Numeric, Text, Index
from sqlalchemy.dialects.postgresql import UUID
from database import Base
from datetime import datetime
import uuid


class CdrRecordDB(Base):
    """Call Detail Record database model"""
    __tablename__ = "cdr_records"
    
    # Base fields
    id = Column(String(36), primary_key=True)
    record_type = Column(String(20), nullable=False, default="CDR")
    timestamp = Column(DateTime, nullable=False, index=True)
    amount = Column(Numeric(10, 2))  # Renamed from charge_amount
    duration = Column(Integer)
    currency = Column(String(10), default="USD")
    
    # Legacy/optional fields
    imsi = Column(String(20))
    imei = Column(String(20))
    
    # Required fields from Java DTO
    status = Column(String(20), nullable=False)
    operator_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    subscriber_msisdn = Column(String(20), nullable=False, index=True)
    
    # CDR specific fields
    call_type = Column(String(20))
    source_number = Column(String(20))
    destination_number = Column(String(20))
    call_direction = Column(String(20))
    success_status = Column(String(20))
    cell_id = Column(String(50))
    location_area_code = Column(String(50))
    network_type = Column(String(10))
    roaming_indicator = Column(Boolean, default=False)
    international_indicator = Column(Boolean, default=False)
    
    __table_args__ = (
        Index('idx_cdr_timestamp_msisdn', 'timestamp', 'subscriber_msisdn'),
    )


class PdrRecordDB(Base):
    """Packet Data Record database model"""
    __tablename__ = "pdr_records"
    
    # Base fields
    id = Column(String(36), primary_key=True)
    record_type = Column(String(20), nullable=False, default="PDR")
    timestamp = Column(DateTime, nullable=False, index=True)
    amount = Column(Numeric(10, 2))  # Renamed from charge_amount
    duration = Column(Integer)
    currency = Column(String(10), default="USD")
    
    # Legacy/optional fields
    imsi = Column(String(20))
    imei = Column(String(20))
    
    # Required fields from Java DTO
    status = Column(String(20), nullable=False)
    operator_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    subscriber_msisdn = Column(String(20), nullable=False, index=True)
    
    # PDR specific fields
    data_volume_bytes = Column(Integer)
    data_volume_mb = Column(Numeric(10, 2))
    apn = Column(String(100))
    service_type = Column(String(50))
    ip_address = Column(String(45))
    url = Column(Text)
    user_agent = Column(Text)
    protocol = Column(String(20))
    port = Column(Integer)
    session_id = Column(String(50))
    bearer_type = Column(String(10))
    roaming_indicator = Column(Boolean, default=False)
    international_indicator = Column(Boolean, default=False)
    payment_method = Column(String(50))
    transaction_id = Column(String(50))
    payment_amount = Column(Numeric(10, 2))
    payment_status = Column(String(20))
    merchant_id = Column(String(50))
    
    __table_args__ = (
        Index('idx_pdr_timestamp_msisdn', 'timestamp', 'subscriber_msisdn'),
    )


class SdrRecordDB(Base):
    """Service Detail Record database model"""
    __tablename__ = "sdr_records"
    
    # Base fields
    id = Column(String(36), primary_key=True)
    record_type = Column(String(20), nullable=False, default="SDR")
    timestamp = Column(DateTime, nullable=False, index=True)
    amount = Column(Numeric(10, 2))  # Renamed from charge_amount
    duration = Column(Integer)
    currency = Column(String(10), default="USD")
    
    # Legacy/optional fields
    imsi = Column(String(20))
    imei = Column(String(20))
    
    # Required fields from Java DTO
    status = Column(String(20), nullable=False)
    operator_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    subscriber_msisdn = Column(String(20), nullable=False, index=True)
    
    # SDR specific fields
    service_name = Column(String(200))
    subscription_type = Column(String(20))
    service_provider = Column(String(200))
    service_id = Column(String(50))
    service_type = Column(String(50))
    subscription_date = Column(DateTime)
    expiration_date = Column(DateTime)
    auto_renewal = Column(Boolean, default=False)
    service_status = Column(String(20))
    billing_cycle = Column(String(20))
    service_features = Column(Text)
    message_type = Column(String(50))
    sender_number = Column(String(20))
    recipient_number = Column(String(20))
    message_length = Column(Integer)
    delivery_status = Column(String(20))
    
    __table_args__ = (
        Index('idx_sdr_timestamp_msisdn', 'timestamp', 'subscriber_msisdn'),
    )


class EdrRecordDB(Base):
    """Event Detail Record database model"""
    __tablename__ = "edr_records"
    
    # Base fields
    id = Column(String(36), primary_key=True)
    record_type = Column(String(20), nullable=False, default="EDR")
    timestamp = Column(DateTime, nullable=False, index=True)
    amount = Column(Numeric(10, 2))  # Renamed from charge_amount
    duration = Column(Integer)
    currency = Column(String(10), default="USD")
    
    # Legacy/optional fields
    imsi = Column(String(20))
    imei = Column(String(20))
    
    # Required fields from Java DTO
    status = Column(String(20), nullable=False)
    operator_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    subscriber_msisdn = Column(String(20), nullable=False, index=True)
    
    # EDR specific fields
    event_type = Column(String(50))
    message_type = Column(String(50))
    content = Column(Text)
    recipient_number = Column(String(20))
    sender_number = Column(String(20))
    message_id = Column(String(50))
    delivery_status = Column(String(20))
    priority_level = Column(Integer)
    is_roaming = Column(Boolean, default=False)
    international_indicator = Column(Boolean, default=False)
    service_type = Column(String(50))
    data_volume = Column(Integer)
    event_description = Column(Text)
    
    __table_args__ = (
        Index('idx_edr_timestamp_msisdn', 'timestamp', 'subscriber_msisdn'),
    )


class TopUpRecordDB(Base):
    """Top-Up Record database model"""
    __tablename__ = "topup_records"
    
    # Base fields
    id = Column(String(36), primary_key=True)
    record_type = Column(String(20), nullable=False, default="TOP_UP")
    timestamp = Column(DateTime, nullable=False, index=True)
    amount = Column(Numeric(10, 2))  # Renamed from charge_amount
    duration = Column(Integer)
    currency = Column(String(10), default="USD")
    
    # Legacy/optional fields
    imsi = Column(String(20))
    imei = Column(String(20))
    
    # Required fields from Java DTO
    status = Column(String(20), nullable=False)
    operator_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    subscriber_msisdn = Column(String(20), nullable=False, index=True)
    
    # TopUp specific fields
    topup_amount = Column(Numeric(10, 2))
    payment_method = Column(String(50))
    topup_type = Column(String(50))
    channel = Column(String(50))
    agent_id = Column(String(50))
    balance_before = Column(Numeric(10, 2))
    balance_after = Column(Numeric(10, 2))
    transaction_id = Column(String(50))
    reference_number = Column(String(50))
    commission_amount = Column(Numeric(10, 2))
    tax_amount = Column(Numeric(10, 2))
    location = Column(String(200))
    terminal_id = Column(String(50))
    receipt_number = Column(String(50))
    topup_channel = Column(String(50))
    voucher_code = Column(String(50))
    subscription_type = Column(String(20))
    validity_period = Column(Integer)
    
    __table_args__ = (
        Index('idx_topup_timestamp_msisdn', 'timestamp', 'subscriber_msisdn'),
    )

