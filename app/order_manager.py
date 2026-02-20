import asyncio
from datetime import datetime, timezone
from app.models import Order, ShippingPriority


class OrderManager:
    """Gestiona las órdenes en memoria, ordenadas por prioridad de envío.

    Thread-safe: usa asyncio.Lock para proteger el dict de órdenes frente
    a accesos concurrentes desde múltiples coroutines.
    """

    def __init__(self):
        self.orders: dict[int, Order] = {}
        self._lock = asyncio.Lock()

    async def add_order(self, order: Order) -> None:
        async with self._lock:
            self.orders[order.order_id] = order

    async def remove_order(self, order_id: int) -> None:
        async with self._lock:
            self.orders.pop(order_id, None)

    def get_sorted_orders(self) -> list[Order]:
        """Regresa las órdenes pendientes ordenadas por prioridad de envío.

        Nota: lectura no bloqueante; la consistencia es eventual pero suficiente
        para dashboards de sólo lectura.
        """
        priority_weight = {
            ShippingPriority.URGENT: 0,
            ShippingPriority.HIGH: 1,
            ShippingPriority.NORMAL: 2,
            ShippingPriority.FULFILLED: 3,
        }
        pending = [o for o in self.orders.values() if not o.is_completed()]
        return sorted(pending, key=lambda o: (
            priority_weight.get(o.shipping_priority, 2),
            o.shipping_deadline or datetime.max.replace(tzinfo=timezone.utc),
        ))

    async def cleanup_completed(self) -> list[int]:
        """Elimina órdenes completadas (entregadas o canceladas). Retorna IDs eliminados."""
        async with self._lock:
            to_remove = [oid for oid, o in self.orders.items() if o.is_completed()]
            for oid in to_remove:
                del self.orders[oid]
            return to_remove

    def get_pending_count(self) -> int:
        return sum(1 for o in self.orders.values() if not o.is_completed())

    def get_urgent_orders(self) -> list[Order]:
        return [
            o for o in self.orders.values()
            if o.shipping_priority == ShippingPriority.URGENT and not o.is_completed()
        ]


# Instancia global
order_manager = OrderManager()
