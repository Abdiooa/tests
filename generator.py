import random
import string
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Set
import uuid
import time
from zoneinfo import ZoneInfo

from models import CdrRecord, PdrRecord, SdrRecord, EdrRecord, TopUpRecord
from enums import (
    RecordStatus, CallType, CallDirection, SuccessStatus, EventType, MessageType,
    DataServiceType, ServiceType, SubscriptionType, PaymentMethod,
    TopUpType, TopUpChannel
)


class XdrRecordGenerator:
    """Generates realistic telecom XDR records matching Java DTO structure"""
    
    def __init__(self):
        # Counter for generating unique sequential values
        self._counter = 0
        self._phone_counter = 0
        self._imsi_counter = 0
        self._imei_counter = 0
        self._decimal_counter = 0
        self.network_types = ["2G", "3G", "4G", "5G"]
        self.apns = ["internet.carrier.com", "mms.carrier.com", "wap.carrier.com"]
        self.urls_base = [
            "https://www.google.com",
            "https://www.youtube.com",
            "https://www.facebook.com",
            "https://www.netflix.com",
            "https://www.twitter.com",
            "https://www.instagram.com",
            "https://www.linkedin.com",
            "https://www.github.com",
            "https://www.stackoverflow.com",
            "https://www.reddit.com"
        ]
        self.user_agents_base = [
            "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)",
            "Mozilla/5.0 (Linux; Android 11; SM-G991B)",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
            "Mozilla/5.0 (X11; Linux x86_64)",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)",
            "Mozilla/5.0 (Linux; Android 12; Pixel 6)"
        ]
        self.service_names_base = [
            "Premium Data Package",
            "Music Streaming",
            "Video Streaming",
            "Cloud Storage",
            "Gaming Package",
            "Enterprise Plan",
            "Family Plan",
            "Student Plan",
            "Unlimited Plan",
            "Basic Plan"
        ]
        self.service_providers_base = ["Carrier Services", "Third Party Provider", "Partner Network", "Premium Services", "Enterprise Solutions"]
        self.locations = ["New York", "Los Angeles", "Chicago", "Houston", "Phoenix", "Philadelphia", "San Antonio", "San Diego", "Dallas", "San Jose"]
        
    def _get_next_counter(self) -> int:
        """Get next unique counter value"""
        self._counter += 1
        return self._counter
    
    def _generate_unique_phone_number(self) -> str:
        """Generate a unique phone number"""
        self._phone_counter += 1
        # Use timestamp + counter for uniqueness
        unique_id = int(time.time() * 1000) % 10000000 + self._phone_counter
        return f"+1555{unique_id:07d}"
    
    def _generate_unique_imsi(self) -> str:
        """Generate a unique IMSI"""
        self._imsi_counter += 1
        # IMSI format: MCC (3 digits) + MNC (2-3 digits) + MSIN (up to 10 digits)
        # Using 310 (US) + random MNC + counter for uniqueness
        unique_id = int(time.time() * 1000) % 100000000000 + self._imsi_counter
        return f"310{unique_id:012d}"
    
    def _generate_unique_imei(self) -> str:
        """Generate a unique IMEI"""
        self._imei_counter += 1
        # IMEI is 15 digits
        unique_id = int(time.time() * 1000) % 100000000000000 + self._imei_counter
        return f"{unique_id:015d}"
    
    def _generate_unique_decimal(self, min_val: float, max_val: float, places: int = 2, record_index: int = 0) -> Decimal:
        """Generate a unique decimal value using counter and record index"""
        self._decimal_counter += 1
        # Use counter, record_index, and microsecond for uniqueness
        range_size = max_val - min_val
        # Combine counter and record_index for unique base
        unique_base = (self._decimal_counter * 1000 + record_index * 17) % int(range_size * 100)
        # Add microsecond component for extra uniqueness
        microsecond_component = (time.time() * 1000000) % 100 / 100.0
        value = round(min_val + (unique_base / 100.0) + (microsecond_component / 1000.0), places)
        # Ensure value is within bounds
        value = min(max(value, min_val), max_val)
        return Decimal(str(value))
    
    def _generate_unique_url(self, index: int) -> str:
        """Generate a unique URL"""
        base_url = self.urls_base[index % len(self.urls_base)]
        unique_param = uuid.uuid4().hex[:8]
        return f"{base_url}?id={unique_param}"
    
    def _generate_unique_user_agent(self, index: int) -> str:
        """Generate a unique user agent"""
        base_ua = self.user_agents_base[index % len(self.user_agents_base)]
        # Add unique identifier
        unique_id = uuid.uuid4().hex[:8]
        return f"{base_ua} [UniqueID: {unique_id}]"
    
    def _generate_unique_service_name(self, index: int) -> str:
        """Generate a unique service name"""
        base_name = self.service_names_base[index % len(self.service_names_base)]
        counter = self._get_next_counter()
        return f"{base_name} {counter}"
    
    def _generate_unique_ip_address(self, index: int) -> str:
        """Generate a unique IP address"""
        # Use index and counter to create unique IPs
        octet1 = 10 + (index % 245)
        octet2 = (self._counter + index) % 256
        octet3 = (self._counter * 2 + index) % 256
        octet4 = (self._counter * 3 + index) % 254 + 1
        return f"{octet1}.{octet2}.{octet3}.{octet4}"
    
    def generate_cdr_record(self, timestamp: datetime, record_index: int = 0) -> CdrRecord:
        """Generate a Call Detail Record matching CdrRecordRequestDto"""
        counter = self._get_next_counter()
        duration = (counter * 13 + record_index * 17) % 3600 + 10  # Unique duration
        success_status = list(SuccessStatus)[(counter + record_index) % len(SuccessStatus)]
        
        # Generate unique identifiers
        unique_operator_id = uuid.uuid4()
        unique_subscriber = self._generate_unique_phone_number()
        unique_source = self._generate_unique_phone_number()
        unique_destination = self._generate_unique_phone_number()
        unique_imsi = self._generate_unique_imsi()
        unique_imei = self._generate_unique_imei()
        unique_cell_id = f"CELL_{counter:06d}_{record_index:04d}"
        unique_lac = f"LAC_{counter:06d}_{record_index:04d}"
        
        return CdrRecord(
            # Required base fields
            record_type="CDR",
            timestamp=timestamp,
            duration=duration if success_status == SuccessStatus.SUCCESS else 0,
            amount=self._generate_unique_decimal(0.05, 5.0, record_index=record_index) if success_status == SuccessStatus.SUCCESS else Decimal("0.0"),
            status=list(RecordStatus)[(counter + record_index * 3) % len(RecordStatus)],
            operator_id=unique_operator_id,
            subscriber_msisdn=unique_subscriber,
            # Optional fields
            id=str(uuid.uuid4()),
            imsi=unique_imsi,
            imei=unique_imei,
            currency="USD",
            # CDR specific fields
            call_type=list(CallType)[(counter + record_index * 2) % len(CallType)],
            source_number=unique_source,
            destination_number=unique_destination,
            call_direction=list(CallDirection)[(counter + record_index * 5) % len(CallDirection)],
            success_status=success_status,
            cell_id=unique_cell_id,
            location_area_code=unique_lac,
            network_type=self.network_types[(counter + record_index * 7) % len(self.network_types)],
            roaming_indicator=(counter + record_index) % 10 == 0,
            international_indicator=(counter + record_index) % 20 == 0
        )
    
    def generate_pdr_record(self, timestamp: datetime, record_index: int = 0) -> PdrRecord:
        """Generate a Packet Data Record matching PdrRecordRequestDto"""
        counter = self._get_next_counter()
        # Generate unique data volume
        data_volume_bytes = (counter * 1024 * 1024 + record_index * 1024 * 1024) % (1073741824 - 1024) + 1024
        data_volume_mb = Decimal(str(round(data_volume_bytes / (1024 * 1024), 2)))
        
        # Generate unique identifiers
        unique_operator_id = uuid.uuid4()
        unique_subscriber = self._generate_unique_phone_number()
        unique_imsi = self._generate_unique_imsi()
        unique_imei = self._generate_unique_imei()
        unique_ip = self._generate_unique_ip_address(record_index)
        unique_url = self._generate_unique_url(record_index)
        unique_user_agent = self._generate_unique_user_agent(record_index)
        unique_session_id = str(uuid.uuid4())
        unique_transaction_id = f"TXN_{uuid.uuid4().hex[:12].upper()}"
        protocols = ["HTTP", "HTTPS", "FTP", "TCP"]
        ports = [80, 443, 8080, 3000]
        payment_methods = ["PREPAID", "POSTPAID"]
        payment_statuses = ["SUCCESS", "PENDING", "FAILED"]
        
        return PdrRecord(
            # Required base fields
            record_type="PDR",
            timestamp=timestamp,
            duration=(counter * 13 + record_index * 17) % 7200 + 60,
            amount=self._generate_unique_decimal(0.01, 10.0, record_index=record_index),
            status=list(RecordStatus)[(counter + record_index * 3) % len(RecordStatus)],
            operator_id=unique_operator_id,
            subscriber_msisdn=unique_subscriber,
            # Optional fields
            id=str(uuid.uuid4()),
            imsi=unique_imsi,
            imei=unique_imei,
            currency="USD",
            # PDR specific fields
            data_volume_bytes=data_volume_bytes,
            data_volume_mb=data_volume_mb,
            apn=self.apns[(counter + record_index) % len(self.apns)],
            service_type=list(DataServiceType)[(counter + record_index * 2) % len(DataServiceType)],
            ip_address=unique_ip,
            url=unique_url,
            user_agent=unique_user_agent,
            protocol=protocols[(counter + record_index * 3) % len(protocols)],
            port=ports[(counter + record_index * 5) % len(ports)],
            session_id=unique_session_id,
            bearer_type=self.network_types[(counter + record_index * 7) % len(self.network_types)],
            roaming_indicator=(counter + record_index) % 10 == 0,
            international_indicator=(counter + record_index) % 20 == 0,
            payment_method=payment_methods[(counter + record_index * 11) % len(payment_methods)],
            transaction_id=unique_transaction_id,
            payment_amount=self._generate_unique_decimal(0.01, 10.0, record_index=record_index),
            payment_status=payment_statuses[(counter + record_index * 13) % len(payment_statuses)],
            merchant_id=f"MERCH_{counter:06d}_{record_index:04d}" if (counter + record_index) % 3 == 0 else None
        )
    
    def generate_sdr_record(self, timestamp: datetime, record_index: int = 0) -> SdrRecord:
        """Generate a Service Detail Record matching SdrRecordRequestDto"""
        counter = self._get_next_counter()
        subscription_date = timestamp - timedelta(days=(counter + record_index * 7) % 365 + 1)
        expiration_periods = [30, 90, 180, 365]
        expiration_days = expiration_periods[(counter + record_index * 11) % len(expiration_periods)]
        
        # Generate unique identifiers
        unique_operator_id = uuid.uuid4()
        unique_subscriber = self._generate_unique_phone_number()
        unique_imsi = self._generate_unique_imsi()
        unique_imei = self._generate_unique_imei()
        unique_service_id = f"SVC_{uuid.uuid4().hex[:8].upper()}"
        unique_service_name = self._generate_unique_service_name(record_index)
        service_providers = self.service_providers_base
        service_statuses = ["ACTIVE", "SUSPENDED", "CANCELLED"]
        billing_cycles = ["DAILY", "WEEKLY", "MONTHLY", "YEARLY"]
        delivery_statuses = ["DELIVERED", "PENDING", "FAILED"]
        
        return SdrRecord(
            # Required base fields
            record_type="SDR",
            timestamp=timestamp,
            duration=(counter * 13 + record_index * 17) % 86400,
            amount=self._generate_unique_decimal(1.0, 50.0, record_index=record_index),
            status=list(RecordStatus)[(counter + record_index * 3) % len(RecordStatus)],
            operator_id=unique_operator_id,
            subscriber_msisdn=unique_subscriber,
            # Optional fields
            id=str(uuid.uuid4()),
            imsi=unique_imsi,
            imei=unique_imei,
            currency="USD",
            # SDR specific fields
            service_name=unique_service_name,
            subscription_type=list(SubscriptionType)[(counter + record_index * 5) % len(SubscriptionType)],
            service_provider=service_providers[(counter + record_index * 7) % len(service_providers)],
            service_id=unique_service_id,
            service_type=list(ServiceType)[(counter + record_index * 9) % len(ServiceType)],
            subscription_date=subscription_date,
            expiration_date=subscription_date + timedelta(days=expiration_days),
            auto_renewal=(counter + record_index) % 10 < 7,
            service_status=service_statuses[(counter + record_index * 11) % len(service_statuses)],
            billing_cycle=billing_cycles[(counter + record_index * 13) % len(billing_cycles)],
            service_features=f'{{"features": ["feature_{counter}", "feature_{record_index}", "feature_{counter + record_index}"]}}',
            delivery_status=delivery_statuses[(counter + record_index * 17) % len(delivery_statuses)]
        )
    
    def generate_edr_record(self, timestamp: datetime, record_index: int = 0) -> EdrRecord:
        """Generate an Event Detail Record matching EdrRecordRequestDto"""
        counter = self._get_next_counter()
        event_type = list(EventType)[(counter + record_index * 3) % len(EventType)]
        
        # Generate unique identifiers
        unique_operator_id = uuid.uuid4()
        unique_subscriber = self._generate_unique_phone_number()
        unique_recipient = self._generate_unique_phone_number()
        unique_sender = self._generate_unique_phone_number()
        unique_imsi = self._generate_unique_imsi()
        unique_imei = self._generate_unique_imei()
        unique_message_id = f"MSG_{uuid.uuid4().hex[:12].upper()}"
        delivery_statuses = ["DELIVERED", "PENDING", "FAILED"]
        service_types = ["SMS", "MMS", "NOTIFICATION"]
        
        # Generate unique content
        unique_content = f"Message content {counter}_{record_index}_{uuid.uuid4().hex[:8]}" if event_type == EventType.SMS else None
        data_volume = (counter * 100 + record_index * 50) % (10000 - 100) + 100 if event_type == EventType.MMS else None
        
        return EdrRecord(
            # Required base fields
            record_type="EDR",
            timestamp=timestamp,
            duration=(counter * 7 + record_index * 11) % 30 + 1,
            amount=self._generate_unique_decimal(0.01, 1.0, record_index=record_index),
            status=list(RecordStatus)[(counter + record_index * 3) % len(RecordStatus)],
            operator_id=unique_operator_id,
            subscriber_msisdn=unique_subscriber,
            # Optional fields
            id=str(uuid.uuid4()),
            imsi=unique_imsi,
            imei=unique_imei,
            currency="USD",
            # EDR specific fields
            event_type=event_type,
            message_type=list(MessageType)[(counter + record_index * 5) % len(MessageType)] if event_type in [EventType.SMS, EventType.MMS] else None,
            content=unique_content,
            recipient_number=unique_recipient,
            sender_number=unique_sender,
            message_id=unique_message_id,
            delivery_status=delivery_statuses[(counter + record_index * 7) % len(delivery_statuses)],
            priority_level=((counter + record_index * 13) % 5) + 1,
            is_roaming=(counter + record_index) % 10 == 0,
            international_indicator=(counter + record_index) % 20 == 0,
            service_type=service_types[(counter + record_index * 17) % len(service_types)],
            data_volume=data_volume,
            event_description=f"Event of type {event_type.value} - ID: {counter}_{record_index}"
        )
    
    def generate_topup_record(self, timestamp: datetime, record_index: int = 0) -> TopUpRecord:
        """Generate a Top-Up Record matching TopUpRecordRequestDto"""
        counter = self._get_next_counter()
        topup_amount = self._generate_unique_decimal(5.0, 100.0, record_index=record_index)
        balance_before = self._generate_unique_decimal(0.0, 50.0, record_index=record_index)
        balance_after = balance_before + topup_amount
        tax_amount = Decimal(str(round(float(topup_amount) * 0.15, 2)))  # 15% tax
        
        # Generate unique identifiers
        unique_operator_id = uuid.uuid4()
        unique_subscriber = self._generate_unique_phone_number()
        unique_imsi = self._generate_unique_imsi()
        unique_imei = self._generate_unique_imei()
        unique_transaction_id = f"TOPUP_{uuid.uuid4().hex[:12].upper()}"
        unique_reference_number = f"REF_{counter:06d}{record_index:03d}"
        unique_terminal_id = f"TERM_{counter:06d}_{record_index:04d}"
        unique_receipt_number = f"RCP_{counter:06d}{record_index:03d}"
        unique_agent_id = f"AGT_{counter:06d}_{record_index:04d}" if (counter + record_index) % 3 == 0 else None
        unique_voucher_code = f"VOUCH_{uuid.uuid4().hex[:10].upper()}" if (counter + record_index) % 3 == 0 else None
        validity_periods = [30, 60, 90, 180, 365]
        
        return TopUpRecord(
            # Required base fields
            record_type="TOP_UP",
            timestamp=timestamp,
            duration=(counter * 11 + record_index * 13) % 60 + 5,
            amount=Decimal("0.0"),
            status=list(RecordStatus)[(counter + record_index * 3) % len(RecordStatus)],
            operator_id=unique_operator_id,
            subscriber_msisdn=unique_subscriber,
            # Optional fields
            id=str(uuid.uuid4()),
            imsi=unique_imsi,
            imei=unique_imei,
            currency="USD",
            # TopUp specific fields
            topup_amount=topup_amount,
            payment_method=list(PaymentMethod)[(counter + record_index * 5) % len(PaymentMethod)],
            topup_type=list(TopUpType)[(counter + record_index * 7) % len(TopUpType)],
            channel=list(TopUpChannel)[(counter + record_index * 9) % len(TopUpChannel)],
            agent_id=unique_agent_id,
            balance_before=balance_before,
            balance_after=balance_after,
            transaction_id=unique_transaction_id,
            reference_number=unique_reference_number,
            commission_amount=self._generate_unique_decimal(0.0, 5.0, record_index=record_index),
            tax_amount=tax_amount,
            location=self.locations[(counter + record_index * 11) % len(self.locations)],
            terminal_id=unique_terminal_id,
            receipt_number=unique_receipt_number,
            voucher_code=unique_voucher_code,
            validity_period=validity_periods[(counter + record_index * 13) % len(validity_periods)]
        )
    
    def generate_batch(self, count_per_type: int = None) -> dict:
        """Generate a batch of all record types - random number (20-50) of each type"""
        # Generate a single timestamp for the entire batch in Africa/Nairobi timezone (UTC+3)
        nairobi_tz = ZoneInfo("Africa/Nairobi")
        batch_timestamp = datetime.now(nairobi_tz)
        
        # Generate random number of records (20-50) for each type
        # Each type gets its own random count for variety
        cdr_count = random.randint(20, 50)
        pdr_count = random.randint(20, 50)
        sdr_count = random.randint(20, 50)
        edr_count = random.randint(20, 50)
        topup_count = random.randint(20, 50)
        
        # Generate records with unique values and shared timestamp
        return {
            "cdr": [self.generate_cdr_record(batch_timestamp, i) for i in range(cdr_count)],
            "pdr": [self.generate_pdr_record(batch_timestamp, i) for i in range(pdr_count)],
            "sdr": [self.generate_sdr_record(batch_timestamp, i) for i in range(sdr_count)],
            "edr": [self.generate_edr_record(batch_timestamp, i) for i in range(edr_count)],
            "topups": [self.generate_topup_record(batch_timestamp, i) for i in range(topup_count)]
        }

