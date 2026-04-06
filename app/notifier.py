import re
import httpx
from app.config import settings
from app.models import Order


def _esc(text: str) -> str:
    """Escapa caracteres especiales para MarkdownV2 de Telegram."""
    return re.sub(r'([_*\[\]()~`>#+=|{}.!\\-])', r'\\\1', str(text))


def _strip_md(text: str) -> str:
    """Quita formato MarkdownV2 para texto plano (ntfy)."""
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'_(.+?)_',   r'\1', text)
    text = re.sub(r'`(.+?)`',   r'\1', text)
    text = re.sub(r'\\(.)',     r'\1', text)
    return text.strip()


class Notifier:
    """Envía notificaciones a Telegram y/o ntfy cuando cambia el estado de una orden."""

    STATUS_LABELS = {
        "confirmed":          ("🛒", "Nueva venta"),
        "payment_required":   ("⏳", "Pago pendiente"),
        "payment_in_process": ("💳", "Pago en proceso"),
        "partially_paid":     ("💳", "Pago parcial"),
        "paid":               ("✅", "Pago confirmado"),
        "shipped":            ("🚚", "Enviado"),
        "delivered":          ("📬", "Entregado"),
        "cancelled":          ("❌", "Cancelado"),
        "invalid":            ("⛔", "Orden inválida"),
    }

    PRIORITY_LABELS = {
        "urgent":    "⚠️ URGENTE",
        "high":      "🔴 Alta",
        "normal":    "🟡 Normal",
        "fulfilled": "✅ Completado",
    }

    # ------------------------------------------------------------------ #
    #  Punto de entrada principal                                          #
    # ------------------------------------------------------------------ #

    async def notify_new_sale(self, order: Order) -> None:
        """Primera vez que vemos esta orden, ya en un estado relevante."""
        markup = None
        if order.status == "paid":
            message = self._build_paid_message(order, previous_status=None)
            markup = self._order_keyboard(order)
        elif order.status == "cancelled":
            message = self._build_cancelled_message(order, previous_status=None)
        elif order.status == "invalid":
            message = self._build_invalid_message(order)
        else:
            return
        await self._send_all(message, urgent=order.shipping_priority.value == "urgent", reply_markup=markup)

    async def notify_order_status(self, order: Order, previous_status: str | None = None) -> None:
        """El estado de una orden conocida cambió a uno relevante."""
        markup = None
        if order.status == "paid":
            message = self._build_paid_message(order, previous_status)
            markup = self._order_keyboard(order)
        elif order.status == "cancelled":
            message = self._build_cancelled_message(order, previous_status)
        elif order.status == "invalid":
            message = self._build_invalid_message(order)
        else:
            return
        await self._send_all(message, urgent=order.shipping_priority.value == "urgent", reply_markup=markup)

    # ------------------------------------------------------------------ #
    #  Teclado inline                                                      #
    # ------------------------------------------------------------------ #

    def _order_keyboard(self, order: Order) -> dict:
        """Botones de acción rápida que aparecen debajo de la notificación."""
        return {
            "inline_keyboard": [[
                {"text": f"📋 Estado #{order.order_id}", "callback_data": f"estado:{order.order_id}"},
                {"text": "📦 Empacar", "callback_data": "empacar"},
            ]]
        }

    # ------------------------------------------------------------------ #
    #  Constructores de mensajes                                           #
    # ------------------------------------------------------------------ #

    def _items_text(self, order: Order) -> str:
        return "\n".join(
            f"  • {_esc(item.title)} ×{item.quantity}"
            + (f" \\(SKU: `{_esc(item.sku)}`\\)" if item.sku else "")
            for item in order.items
        )

    def _build_paid_message(self, order: Order, previous_status: str | None) -> str:
        priority_label = self.PRIORITY_LABELS.get(order.shipping_priority.value, "")

        if previous_status:
            prev_emoji, prev_label = self.STATUS_LABELS.get(previous_status, ("📋", previous_status))
            header = (
                f"✅ *Pago confirmado*\n"
                f"\\#{order.order_id} · antes: {prev_emoji} {_esc(prev_label)}"
            )
        else:
            header = f"🛒 *Nueva venta pagada*\n\\#{order.order_id}"

        lines = [
            header,
            "",
            f"👤 *{_esc(order.buyer_nickname)}*",
            f"💰 ${_esc(f'{order.total_amount:,.2f}')}",
            f"📦 {_esc(priority_label)}",
            "",
            f"*Artículos:*\n{self._items_text(order)}",
        ]

        if order.shipping_deadline:
            lines.append(f"\n⏰ Límite de envío: {_esc(order.shipping_deadline.strftime('%d/%m %H:%M'))}")

        return "\n".join(lines)

    def _build_cancelled_message(self, order: Order, previous_status: str | None) -> str:
        lines = [
            f"❌ *Cancelado*\n\\#{order.order_id}",
            "",
            f"👤 {_esc(order.buyer_nickname)}",
            f"💰 ${_esc(f'{order.total_amount:,.2f}')}",
            "",
            f"*Artículos:*\n{self._items_text(order)}",
        ]
        return "\n".join(lines)

    def _build_invalid_message(self, order: Order) -> str:
        lines = [
            f"⛔ *Orden inválida \\(fraude\\)*\n\\#{order.order_id}",
            "",
            f"👤 {_esc(order.buyer_nickname)}",
            f"💰 ${_esc(f'{order.total_amount:,.2f}')}",
        ]
        return "\n".join(lines)

    # ------------------------------------------------------------------ #
    #  Envío a canales                                                     #
    # ------------------------------------------------------------------ #

    async def _send_all(self, message: str, urgent: bool = False, reply_markup: dict | None = None) -> None:
        async with httpx.AsyncClient(timeout=10) as client:
            if settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID:
                await self._send_telegram(client, message, urgent, reply_markup)
            if settings.NTFY_TOPIC:
                await self._send_ntfy(client, message, urgent)

    async def _send_telegram(
        self,
        client: httpx.AsyncClient,
        message: str,
        urgent: bool,
        reply_markup: dict | None = None,
    ) -> None:
        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
        payload: dict = {
            "chat_id": settings.TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "MarkdownV2",
            "disable_notification": not urgent,
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        try:
            await client.post(url, json=payload)
        except Exception as e:
            print(f"[Notifier] Error enviando a Telegram: {e}")

    async def _send_ntfy(self, client: httpx.AsyncClient, message: str, urgent: bool) -> None:
        lines = message.split("\n", 1)
        title = _strip_md(lines[0])
        body = _strip_md(lines[1]) if len(lines) > 1 else ""
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
