from fastapi import APIRouter, Request
from datetime import datetime, timezone
from app.models import WebhookPayload, Order, OrderItem, ShippingPriority
from app.meli_client import meli
from app.order_manager import order_manager

router = APIRouter()


def classify_shipping_priority(shipment: dict) -> ShippingPriority:
    """Clasifica la prioridad según el tipo de envío y fecha límite."""
    status = shipment.get("status", "")
    if status in ("delivered", "cancelled"):
        return ShippingPriority.FULFILLED

    shipping_type = shipment.get("logistic_type", "")
    # Fulfillment o same-day = urgente
    if shipping_type in ("fulfillment", "same_day", "next_day"):
        return ShippingPriority.URGENT

    # Revisar fecha límite de despacho
    deadline = shipment.get("shipping_option", {}).get("estimated_handling_limit", {}).get("date")
    if deadline:
        deadline_dt = datetime.fromisoformat(deadline.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        hours_left = (deadline_dt - now).total_seconds() / 3600
        if hours_left <= 24:
            return ShippingPriority.URGENT
        elif hours_left <= 48:
            return ShippingPriority.HIGH

    return ShippingPriority.NORMAL


@router.post("/receive")
async def receive_webhook(payload: WebhookPayload):
    """Recibe notificaciones de ML (directo o reenviado desde tu otra página)."""

    if payload.topic == "orders_v2":
        # Extraer order_id del resource: /orders/12345
        order_id = payload.resource.split("/")[-1]
        try:
            order_data = await meli.get_order(order_id)

            # Obtener info de envío si existe
            shipping_id = order_data.get("shipping", {}).get("id")
            priority = ShippingPriority.NORMAL
            deadline = None

            if shipping_id:
                shipment = await meli.get_shipment(str(shipping_id))
                priority = classify_shipping_priority(shipment)
                dl = shipment.get("shipping_option", {}).get(
                    "estimated_handling_limit", {}
                ).get("date")
                if dl:
                    deadline = datetime.fromisoformat(dl.replace("Z", "+00:00"))

            items = [
                OrderItem(
                    item_id=item["item"]["id"],
                    title=item["item"]["title"],
                    quantity=item["quantity"],
                    sku=item["item"].get("seller_sku"),
                )
                for item in order_data.get("order_items", [])
            ]

            order = Order(
                order_id=int(order_id),
                buyer_nickname=order_data.get("buyer", {}).get("nickname", ""),
                items=items,
                shipping_id=shipping_id,
                shipping_priority=priority,
                shipping_deadline=deadline,
                status=order_data.get("status", "pending"),
                date_created=order_data.get("date_created", datetime.now(timezone.utc).isoformat()),
                total_amount=order_data.get("total_amount", 0),
            )

            # Si ya está completada, la eliminamos; si no, la agregamos
            if order.is_completed():
                order_manager.remove_order(order.order_id)
            else:
                order_manager.add_order(order)

            return {"status": "processed", "order_id": order_id, "priority": priority}

        except Exception as e:
            return {"status": "error", "detail": str(e)}

    return {"status": "ignored", "topic": payload.topic}


@router.post("/forward")
async def forward_from_external(request: Request):
    """Endpoint para reenviar notificaciones desde tu otra página."""
    body = await request.json()
    # Reenviar al procesador principal
    payload = WebhookPayload(**body)
    return await receive_webhook(payload)
