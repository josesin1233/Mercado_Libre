from fastapi import APIRouter
from app.order_manager import order_manager
from app.models import NotificationMessage, ShippingPriority

router = APIRouter()


@router.get("/pending")
def get_pending_notifications() -> list[NotificationMessage]:
    """Genera las notificaciones pendientes para enviar al teléfono."""
    messages = []

    urgent = order_manager.get_urgent_orders()
    if urgent:
        items_text = []
        for order in urgent:
            for item in order.items:
                items_text.append(f"- {item.title} x{item.quantity}")

        messages.append(NotificationMessage(
            title=f"⚠️ {len(urgent)} envío(s) urgente(s)",
            body=f"Productos por enviar:\n" + "\n".join(items_text),
            priority=ShippingPriority.URGENT,
        ))

    orders = order_manager.get_sorted_orders()
    if orders:
        # Resumen general
        messages.append(NotificationMessage(
            title=f"📦 {len(orders)} orden(es) pendiente(s)",
            body=f"Urgentes: {len(urgent)} | Total: {len(orders)}",
            priority=ShippingPriority.NORMAL,
        ))

    return messages


@router.get("/what-to-pack")
def what_to_pack():
    """Lista qué productos empacar, en orden de prioridad."""
    orders = order_manager.get_sorted_orders()
    pack_list = []
    for order in orders:
        for item in order.items:
            pack_list.append({
                "order_id": order.order_id,
                "priority": order.shipping_priority,
                "deadline": order.shipping_deadline,
                "title": item.title,
                "quantity": item.quantity,
                "sku": item.sku,
            })
    return {"pack_list": pack_list, "total_items": len(pack_list)}
