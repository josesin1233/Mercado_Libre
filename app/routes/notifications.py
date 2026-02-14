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


@router.get("/stock-alert")
def stock_alert():
    """Muestra qué productos se están vendiendo más para saber qué hace falta."""
    orders = order_manager.get_sorted_orders()
    product_count: dict[str, dict] = {}

    for order in orders:
        for item in order.items:
            key = item.item_id
            if key not in product_count:
                product_count[key] = {
                    "item_id": item.item_id,
                    "title": item.title,
                    "sku": item.sku,
                    "total_sold": 0,
                }
            product_count[key]["total_sold"] += item.quantity

    # Ordenar por más vendido
    sorted_products = sorted(
        product_count.values(),
        key=lambda x: x["total_sold"],
        reverse=True,
    )

    return {"products": sorted_products}


@router.get("/phone-summary")
def phone_summary():
    """Resumen compacto pensado para notificación push al teléfono."""
    orders = order_manager.get_sorted_orders()
    urgent = order_manager.get_urgent_orders()

    if not orders:
        return {"notification": {"title": "✅ Sin pendientes", "body": "No hay órdenes por enviar."}}

    next_order = orders[0]
    items_text = ", ".join([f"{i.title} x{i.quantity}" for i in next_order.items])

    return {
        "notification": {
            "title": f"📦 {len(orders)} pendientes | ⚠️ {len(urgent)} urgentes",
            "body": f"Siguiente: {items_text}",
            "data": {
                "total": len(orders),
                "urgent": len(urgent),
                "next_order_id": next_order.order_id,
            },
        }
    }
