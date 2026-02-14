from fastapi import APIRouter
from app.order_manager import order_manager

router = APIRouter()


@router.get("/")
def list_orders():
    """Lista todas las órdenes pendientes ordenadas por prioridad de envío."""
    orders = order_manager.get_sorted_orders()
    return {
        "total_pending": len(orders),
        "orders": [o.model_dump() for o in orders],
    }


@router.get("/urgent")
def list_urgent():
    """Lista solo las órdenes urgentes."""
    urgent = order_manager.get_urgent_orders()
    return {
        "total_urgent": len(urgent),
        "orders": [o.model_dump() for o in urgent],
    }


@router.post("/cleanup")
def cleanup_orders():
    """Elimina las órdenes ya completadas (entregadas/canceladas)."""
    removed = order_manager.cleanup_completed()
    return {
        "removed_count": len(removed),
        "removed_ids": removed,
        "remaining": order_manager.get_pending_count(),
    }


@router.get("/summary")
def orders_summary():
    """Resumen rápido de la situación actual."""
    orders = order_manager.get_sorted_orders()
    urgent = order_manager.get_urgent_orders()
    return {
        "total_pending": len(orders),
        "urgent": len(urgent),
        "next_to_ship": orders[0].model_dump() if orders else None,
    }
