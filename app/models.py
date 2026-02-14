from pydantic import BaseModel
from datetime import datetime
from enum import Enum


class ShippingPriority(str, Enum):
    URGENT = "urgent"        # Envío hoy / ME2
    HIGH = "high"            # Envío mañana
    NORMAL = "normal"        # Envío estándar
    FULFILLED = "fulfilled"  # Ya enviado


class OrderItem(BaseModel):
    item_id: str
    title: str
    quantity: int
    sku: str | None = None


class Order(BaseModel):
    order_id: int
    buyer_nickname: str
    items: list[OrderItem]
    shipping_id: int | None = None
    shipping_priority: ShippingPriority = ShippingPriority.NORMAL
    shipping_deadline: datetime | None = None
    status: str = "pending"
    date_created: datetime
    total_amount: float

    def is_completed(self) -> bool:
        return self.status in ("delivered", "cancelled")


class WebhookPayload(BaseModel):
    resource: str
    user_id: int
    topic: str
    application_id: int | None = None
    attempts: int = 1
    sent: str | None = None
    received: str | None = None


class NotificationMessage(BaseModel):
    title: str
    body: str
    priority: ShippingPriority = ShippingPriority.NORMAL
