from enum import Enum


class RecordStatus(str, Enum):
    """Status of the record"""
    PENDING = "PENDING"
    PROCESSED = "PROCESSED"
    FAILED = "FAILED"
    REJECTED = "REJECTED"


class CallType(str, Enum):
    VOICE = "VOICE"
    VIDEO = "VIDEO"
    CONFERENCE = "CONFERENCE"
    VOICEMAIL = "VOICEMAIL"


class CallDirection(str, Enum):
    INCOMING = "INCOMING"
    OUTGOING = "OUTGOING"
    FORWARDED = "FORWARDED"


class SuccessStatus(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    BUSY = "BUSY"
    NO_ANSWER = "NO_ANSWER"
    REJECTED = "REJECTED"


class EventType(str, Enum):
    SMS = "SMS"
    MMS = "MMS"
    USSD = "USSD"
    NOTIFICATION = "NOTIFICATION"
    SYSTEM_EVENT = "SYSTEM_EVENT"
    SERVICE_REQUEST = "SERVICE_REQUEST"


class MessageType(str, Enum):
    SMS = "SMS"
    MMS = "MMS"
    FLASH_SMS = "FLASH_SMS"
    BINARY_SMS = "BINARY_SMS"


class DataServiceType(str, Enum):
    INTERNET = "INTERNET"
    STREAMING = "STREAMING"
    SOCIAL_MEDIA = "SOCIAL_MEDIA"
    EMAIL = "EMAIL"
    VPN = "VPN"
    GAMING = "GAMING"
    FILE_DOWNLOAD = "FILE_DOWNLOAD"


class ServiceType(str, Enum):
    VOICE = "VOICE"
    DATA = "DATA"
    SMS = "SMS"
    MMS = "MMS"
    VALUE_ADDED = "VALUE_ADDED"
    ROAMING = "ROAMING"
    ENTERTAINMENT = "ENTERTAINMENT"


class SubscriptionType(str, Enum):
    PREPAID = "PREPAID"
    POSTPAID = "POSTPAID"
    HYBRID = "HYBRID"


class PaymentMethod(str, Enum):
    CREDIT_CARD = "CREDIT_CARD"
    DEBIT_CARD = "DEBIT_CARD"
    MOBILE_MONEY = "MOBILE_MONEY"
    CASH = "CASH"
    VOUCHER = "VOUCHER"
    BANK_TRANSFER = "BANK_TRANSFER"


class TopUpType(str, Enum):
    REGULAR = "REGULAR"
    BONUS = "BONUS"
    PROMOTIONAL = "PROMOTIONAL"
    EMERGENCY = "EMERGENCY"


class TopUpChannel(str, Enum):
    MOBILE_APP = "MOBILE_APP"
    USSD = "USSD"
    WEB = "WEB"
    AGENT = "AGENT"
    ATM = "ATM"
    RETAIL_STORE = "RETAIL_STORE"

