from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional
from decimal import Decimal
from uuid import UUID
from enums import (
    RecordStatus, CallType, CallDirection, SuccessStatus, EventType, MessageType,
    DataServiceType, ServiceType, SubscriptionType, PaymentMethod,
    TopUpType, TopUpChannel
)


class XdrRecord(BaseModel):
    """Base model for all XDR records - minimal required fields"""
    # Required base fields (matching Java entity)
    record_type: str = Field(alias="recordType")  # Required
    timestamp: datetime  # Required - Individual record timestamp
    amount: Optional[Decimal] = Field(None, decimal_places=2)  # Optional BigDecimal
    
    # Optional fields
    id: Optional[str] = None  # Can be generated server-side
    duration: Optional[int] = None  # Duration in seconds (Long in Java)
    currency: Optional[str] = "USD"  # Currency code
    
    # Legacy fields for backward compatibility
    imsi: Optional[str] = None  # International Mobile Subscriber Identity
    imei: Optional[str] = None  # International Mobile Equipment Identity
    
    model_config = ConfigDict(
        use_enum_values=True,
        populate_by_name=True,  # Allow both snake_case and camelCase
        # Pydantic v2 automatically serializes timezone-aware datetimes with ISO format including timezone
        # Example: "2025-11-05T09:50:46.415101+03:00"
    )


class CdrRecord(XdrRecord):
    """Call Detail Record - matches CdrRecordRequestDto"""
    # Required fields from Java DTO
    status: RecordStatus
    operator_id: UUID = Field(alias="operatorId")
    subscriber_msisdn: str = Field(alias="subscriberMsisdn")
    call_type: CallType = Field(alias="callType")
    source_number: str = Field(alias="sourceNumber")
    destination_number: str = Field(alias="destinationNumber")
    call_direction: CallDirection = Field(alias="callDirection")
    success_status: SuccessStatus = Field(alias="successStatus")
    
    # Optional fields
    cell_id: Optional[str] = Field(None, alias="cellId")
    location_area_code: Optional[str] = Field(None, alias="locationAreaCode")
    network_type: Optional[str] = None  # 2G, 3G, 4G, 5G
    roaming_indicator: Optional[bool] = Field(None, alias="roamingIndicator")
    international_indicator: Optional[bool] = Field(None, alias="internationalIndicator")


class EdrRecord(XdrRecord):
    """Event Detail Record - matches EdrRecordRequestDto"""
    # Required fields from Java DTO
    status: RecordStatus
    operator_id: UUID = Field(alias="operatorId")
    subscriber_msisdn: str = Field(alias="subscriberMsisdn")
    event_type: EventType = Field(alias="eventType")
    
    # Optional fields
    message_type: Optional[MessageType] = Field(None, alias="messageType")
    content: Optional[str] = None
    recipient_number: Optional[str] = Field(None, alias="recipientNumber")
    sender_number: Optional[str] = Field(None, alias="senderNumber")
    message_id: Optional[str] = Field(None, alias="messageId")
    delivery_status: Optional[str] = Field(None, alias="deliveryStatus")
    priority_level: Optional[int] = Field(None, alias="priorityLevel")
    is_roaming: Optional[bool] = Field(None, alias="isRoaming")
    international_indicator: Optional[bool] = Field(None, alias="internationalIndicator")
    service_type: Optional[str] = Field(None, alias="serviceType")
    data_volume: Optional[int] = Field(None, alias="dataVolume")
    event_description: Optional[str] = Field(None, alias="eventDescription")


class PdrRecord(XdrRecord):
    """Packet Data Record - matches PdrRecordRequestDto"""
    # Required fields from Java DTO
    status: RecordStatus
    operator_id: UUID = Field(alias="operatorId")
    subscriber_msisdn: str = Field(alias="subscriberMsisdn")
    
    # Optional PDR specific fields
    data_volume_bytes: Optional[int] = Field(None, alias="dataVolumeBytes")
    data_volume_mb: Optional[Decimal] = Field(None, decimal_places=2, alias="dataVolumeMB")
    apn: Optional[str] = None  # Access Point Name
    service_type: Optional[DataServiceType] = Field(None, alias="serviceType")
    ip_address: Optional[str] = Field(None, alias="ipAddress")
    url: Optional[str] = None
    user_agent: Optional[str] = Field(None, alias="userAgent")
    protocol: Optional[str] = None  # HTTP, HTTPS, FTP, etc.
    port: Optional[int] = None
    session_id: Optional[str] = Field(None, alias="sessionId")
    bearer_type: Optional[str] = Field(None, alias="bearerType")  # 2G, 3G, 4G, 5G
    roaming_indicator: Optional[bool] = Field(None, alias="roamingIndicator")
    international_indicator: Optional[bool] = Field(None, alias="internationalIndicator")
    payment_method: Optional[str] = Field(None, alias="paymentMethod")
    transaction_id: Optional[str] = Field(None, alias="transactionId")
    payment_amount: Optional[Decimal] = Field(None, decimal_places=2, alias="paymentAmount")
    payment_status: Optional[str] = Field(None, alias="paymentStatus")
    merchant_id: Optional[str] = Field(None, alias="merchantId")


class SdrRecord(XdrRecord):
    """Service Detail Record - matches SdrRecordRequestDto"""
    # Required fields from Java DTO
    status: RecordStatus
    operator_id: UUID = Field(alias="operatorId")
    subscriber_msisdn: str = Field(alias="subscriberMsisdn")
    service_name: str = Field(alias="serviceName")
    
    # Optional fields
    subscription_type: Optional[SubscriptionType] = Field(None, alias="subscriptionType")
    service_provider: Optional[str] = Field(None, alias="serviceProvider")
    service_id: Optional[str] = Field(None, alias="serviceId")
    service_type: Optional[ServiceType] = Field(None, alias="serviceType")
    subscription_date: Optional[datetime] = Field(None, alias="subscriptionDate")
    expiration_date: Optional[datetime] = Field(None, alias="expirationDate")
    auto_renewal: Optional[bool] = Field(None, alias="autoRenewal")
    service_status: Optional[str] = Field(None, alias="serviceStatus")  # ACTIVE, SUSPENDED, CANCELLED
    billing_cycle: Optional[str] = Field(None, alias="billingCycle")  # DAILY, WEEKLY, MONTHLY, YEARLY
    service_features: Optional[str] = Field(None, alias="serviceFeatures")
    message_type: Optional[str] = Field(None, alias="messageType")
    sender_number: Optional[str] = Field(None, alias="senderNumber")
    recipient_number: Optional[str] = Field(None, alias="recipientNumber")
    message_length: Optional[int] = Field(None, alias="messageLength")
    delivery_status: Optional[str] = Field(None, alias="deliveryStatus")


class TopUpRecord(XdrRecord):
    """Top-Up Record - matches TopUpRecordRequestDto"""
    # Required fields from Java DTO
    status: RecordStatus
    operator_id: UUID = Field(alias="operatorId")
    subscriber_msisdn: str = Field(alias="subscriberMsisdn")
    topup_amount: Decimal = Field(decimal_places=2, alias="topUpAmount")
    payment_method: PaymentMethod = Field(alias="paymentMethod")
    channel: TopUpChannel
    
    # Optional fields
    topup_type: Optional[TopUpType] = Field(None, alias="topUpType")
    agent_id: Optional[str] = Field(None, alias="agentId")
    balance_before: Optional[Decimal] = Field(None, decimal_places=2, alias="balanceBefore")
    balance_after: Optional[Decimal] = Field(None, decimal_places=2, alias="balanceAfter")
    transaction_id: Optional[str] = Field(None, alias="transactionId")
    reference_number: Optional[str] = Field(None, alias="referenceNumber")
    commission_amount: Optional[Decimal] = Field(None, decimal_places=2, alias="commissionAmount")
    tax_amount: Optional[Decimal] = Field(None, decimal_places=2, alias="taxAmount")
    location: Optional[str] = None
    terminal_id: Optional[str] = Field(None, alias="terminalId")
    receipt_number: Optional[str] = Field(None, alias="receiptNumber")
    topup_channel: Optional[str] = Field(None, alias="topUpChannel")
    voucher_code: Optional[str] = Field(None, alias="voucherCode")
    subscription_type: Optional[str] = Field(None, alias="subscriptionType")
    validity_period: Optional[int] = Field(None, alias="validityPeriod")


class XdrDataResponse(BaseModel):
    """Response model for /api/data endpoint"""
    timestamp: datetime
    total_records: int
    cdr: list[CdrRecord] = []
    pdr: list[PdrRecord] = []
    sdr: list[SdrRecord] = []
    edr: list[EdrRecord] = []
    topups: list[TopUpRecord] = []

