import httpx
from app.config import settings
from app.models import Order


class Notifier:
    """Envía notificaciones a Telegram y/o ntfy cuando cambia el estado de una orden."""

    # Emojis y etiquetas por estado de ML
    STATUS_LABELS = {
        "confirmed":        ("🛒", "Nueva venta"),
        "payment_required": ("⏳", "Pago pendiente"),
        "payment_in_process": ("💳", "Pago en proceso"),
        "partially_paid":   ("💳", "Pago parcial"),
        "paid":             ("✅", "Pago confirmado"),
        "shipped":          ("🚚", "Enviado"),
        "delivered":        ("📬", "Entregado"),
        "cancelled":        ("❌", "Cancelado"),
    }

    PRIORITY_LABELS = {
        "urgent": "⚠️ URGENTE",
        "high":   "🔴 Alta",
        "normal": "🟡 Normal",
        "fulfilled": "✅ Completado",
    }

    # ------------------------------------------------------------------ #
    #  Punto de entrada principal                                          #
    # ------------------------------------------------------------------ #

    async def notify_order_status(self, order: Order, previous_status: str | None = None) -> None:
        """Manda notificación cuando una orden cambia de estado."""
        message = self._build_order_message(order, previous_status)
        await self._send_all(message, urgent=order.shipping_priority.value == "urgent")

    async def notify_new_sale(self, order: Order) -> None:
        """Manda notificación específica para venta nueva."""
        message = self._build_sale_message(order)
        await self._send_all(message, urgent=False)

    # ------------------------------------------------------------------ #
    #  Constructores de mensajes                                           #
    # ------------------------------------------------------------------ #

    def _build_order_message(self, order: Order, previous_status: str | None) -> str:
        emoji, label = self.STATUS_LABELS.get(order.status, ("📋", order.status))
        priority_label = self.PRIORITY_LABELS.get(order.shipping_priority.value, "")

        items_text = "\n".join(
            f"  • {item.title} x{item.quantity}" + (f" (SKU: {item.sku})" if item.sku else "")
            for item in order.items
        )

        lines = [
            f"{emoji} *{label}* — Orden #{order.order_id}",
            f"👤 Comprador: {order.buyer_nickname}",
            f"💰 Total: ${order.total_amount:,.2f}",
            f"📦 Prioridad: {priority_label}",
            f"\n*Productos:*\n{items_text}",
        ]

        if previous_status and previous_status != order.status:
            prev_emoji, prev_label = self.STATUS_LABELS.get(previous_status, ("📋", previous_status))
            lines.insert(1, f"🔄 {prev_emoji} {prev_label} → {emoji} {label}")

        if order.shipping_deadline:
            deadline_str = order.shipping_deadline.strftime("%d/%m %H:%M")
            lines.append(f"⏰ Límite de envío: {deadline_str}")

        return "\n".join(lines)

    def _build_sale_message(self, order: Order) -> str:
        items_text = "\n".join(
            f"  • {item.title} x{item.quantity}"
            for item in order.items
        )
        return (
            f"🛒 *Nueva venta en ML*\n"
            f"👤 {order.buyer_nickname}\n"
            f"💰 ${order.total_amount:,.2f}\n"
            f"\n*Productos:*\n{items_text}"
        )

    # ------------------------------------------------------------------ #
    #  Envío a canales                                                     #
    # ------------------------------------------------------------------ #

    async def _send_all(self, message: str, urgent: bool = False) -> None:
        async with httpx.AsyncClient(timeout=10) as client:
            if settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID:
                await self._send_telegram(client, message, urgent)
            if settings.NTFY_TOPIC:
                await self._send_ntfy(client, message, urgent)

    async def _send_telegram(self, client: httpx.AsyncClient, message: str, urgent: bool) -> None:
        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
        try:
            await client.post(url, json={
                "chat_id": settings.TELEGRAM_CHAT_ID,
                "text": message,
                "parse_mode": "Markdown",
                "disable_notification": not urgent,  # silencia notis no urgentes
            })
        except Exception as e:
            print(f"[Notifier] Error enviando a Telegram: {e}")

    async def _send_ntfy(self, client: httpx.AsyncClient, message: str, urgent: bool) -> None:
        # Primera línea del mensaje como título, resto como body
        lines = message.split("\n", 1)
        title = lines[0].replace("*", "").strip()
        body = lines[1].strip() if len(lines) > 1 else ""

        try:
            await client.post(
                "https://ntfy.sh",
                json={
                    "topic": settings.NTFY_TOPIC,
                    "title": title,
                    "message": body,
                    "priority": 5 if urgent else 3,
                    "tags": ["warning"] if urgent else ["shopping_cart"],
                },
            )
        except Exception as e:
            print(f"[Notifier] Error enviando a ntfy: {e}")


notifier = Notifier()
