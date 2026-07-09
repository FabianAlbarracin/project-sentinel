from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional


class ObservationType(str, Enum):
    PRODUCT = "PRODUCT"
    COUPON = "COUPON"
    POST = "POST"
    UNKNOWN = "UNKNOWN"


class TermType(str, Enum):
    ANCHOR = "ANCHOR"
    EXCLUDE = "EXCLUDE"


class NotificationStatus(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


@dataclass(frozen=True)
class Source:
    id: int
    name: str
    enabled: bool
    created_at: datetime


@dataclass(frozen=True)
class WatchItem:
    id: int
    name: str
    enabled: bool
    created_at: datetime


@dataclass(frozen=True)
class WatchTerm:
    id: int
    watch_item_id: int
    term: str
    term_type: TermType
    created_at: datetime


@dataclass(frozen=True)
class Observation:
    id: Optional[int] = None
    source_id: Optional[int] = None
    watch_item_id: Optional[int] = None
    external_id: Optional[str] = None
    observed_at: Optional[datetime] = None
    observation_type: ObservationType = ObservationType.UNKNOWN
    title: Optional[str] = None
    price: Optional[Decimal] = None
    currency: Optional[str] = None
    coupon: Optional[str] = None
    url: Optional[str] = None
    raw_content: Optional[str] = None
    created_at: Optional[datetime] = None


@dataclass(frozen=True)
class Notification:
    id: Optional[int] = None
    observation_id: Optional[int] = None
    channel: str = "telegram"
    status: NotificationStatus = NotificationStatus.SUCCESS
    sent_at: Optional[datetime] = None
