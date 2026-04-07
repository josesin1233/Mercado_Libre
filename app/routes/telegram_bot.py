"""Comandos del bot de Telegram para consultar órdenes."""

import re
import httpx
from fastapi import APIRouter, Request
from app.config import settings
from app.models import Order, ShippingPriority
from app.order_manager import order_manager

router = APIRouter()

PRIORITY_EMOJI = {
    "urgent":    "⚠️",
    "high":      "🔴",
    "normal":    "🟡",
    "fulfilled": "✅",
}

STATUS_LABELS = {
    "confirmed":          "Nueva venta",
    "payment_required":   "Pago pendiente",
    "payment_in_process": "Pago en proceso",
    "partially_paid":     "Pago parcial",
    "paid":               "Pagado",
    "shipped":            "Enviado",
    "delivered":          "Entregado",
    "cancelled":          "Cancelado",
    "invalid":            "Orden inválida",
}

PRIORITY_LABELS = {
    "urgent":    "⚠️ URGENTE",
    "high":      "🔴 Alta",
    "normal":    "🟡 Normal",
    "fulfilled": "✅ Completado",
}


def _esc(text: str) -> str:
    """Escapa caracteres especiales para MarkdownV2 de Telegram."""
    return re.sub(r'([_*\[\]()~`>#+=|{}.!\\-])', r'\\\1', str(text))


async def _reply(chat_id: int, text: str, reply_markup: dict | None = None) -> None:
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload: dict = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "MarkdownV2",
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(url, json=payload)
        if not r.json().get("ok"):
            # Fallback: enviar sin formato si falla el MarkdownV2
            plain = re.sub(r'\\(.)', r'\1', re.sub(r'[*_`~]', '', text))
            payload["text"] = plain
            del payload["parse_mode"]
            await client.post(url, json=payload)


async def _answer_callback(callback_query_id: str) -> None:
    """Confirma el callback para quitar el spinner del botón."""
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/answerCallbackQuery"
    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(url, json={"callback_query_id": callback_query_id})


def _parse_command(text: str) -> tuple[str, str]:
    """Separa el comando del argumento. Elimina @BotName si viene de grupo."""
    parts = text.strip().split(None, 1)
    cmd = parts[0].split("@")[0].lower()
    arg = parts[1].strip() if len(parts) > 1 else ""
    return cmd, arg


def _is_authorized(chat_id: int) -> bool:
    return str(chat_id) == str(settings.TELEGRAM_CHAT_ID)


# ------------------------------------------------------------------ #
#  Helper: tarjeta de una orden                                       #
# ------------------------------------------------------------------ #

def _pending_orders() -> list[Order]:
    """Órdenes pagadas que aún no han sido enviadas."""
    return [
        o for o in order_manager.get_sorted_orders()
        if o.status == "paid" and o.shipping_priority != ShippingPriority.FULFILLED
    ]


async def _send_order_card(chat_id: int, order: Order) -> None:
    """Manda un mensaje completo por orden (todos sus artículos juntos)."""
    emoji = PRIORITY_EMOJI.get(order.shipping_priority.value, "📋")
    priority = _esc(PRIORITY_LABELS.get(order.shipping_priority.value, ""))
    item_lines = []
    for i in order.items:
        line = f"  • {_esc(i.title)}"
        if i.variation:
            line += f" — {_esc(i.variation)}"
        line += f" ×{i.quantity}"
        if i.sku:
            line += f" \`{_esc(i.sku)}\`"
        item_lines.append(line)
    items = "\n".join(item_lines)
    deadline = (
        f"\n📅 Enviar antes del: *{_esc(order.shipping_deadline.strftime('%d/%m/%Y %H:%M'))}*"
        if order.shipping_deadline else ""
    )

    msg = (
        f"{emoji} *Pedido \\#{order.order_id}* — {priority}\n"
        f"👤 {_esc(order.buyer_nickname)}\n"
        f"💰 ${_esc(f'{order.total_amount:,.2f}')}"
        f"{deadline}\n"
        f"\n*Artículos:*\n{items}"
    )
    markup = {
        "inline_keyboard": [[
            {"text": "🔗 Ver en ML", "url": f"https://www.mercadolibre.com.mx/ventas/{order.order_id}/detalle"},
            {"text": "📋 Estado", "callback_data": f"estado:{order.order_id}"},
        ]]
    }
    await _reply(chat_id, msg, reply_markup=markup)


# ------------------------------------------------------------------ #
#  Handlers de comandos                                               #
# ------------------------------------------------------------------ #

LIMIT = 15


async def _cmd_pedidos(chat_id: int) -> None:
    orders = _pending_orders()
    if not orders:
        await _reply(chat_id, "✅ No hay pedidos pendientes\\.")
        return

    total = len(orders)
    word = "pedido" if total == 1 else "pedidos"
    await _reply(chat_id, f"📦 *{total} {word} pendientes:*")

    for o in orders[:LIMIT]:
        await _send_order_card(chat_id, o)

    if total > LIMIT:
        await _reply(chat_id, f"_\\.\\.\\. y {total - LIMIT} más — usa /estado `<id>` para ver uno específico_")


async def _cmd_urgentes(chat_id: int) -> None:
    orders = [o for o in order_manager.get_urgent_orders() if o.status == "paid"]
    if not orders:
        await _reply(chat_id, "✅ No hay pedidos urgentes\\.")
        return

    total = len(orders)
    word = "pedido urgente" if total == 1 else "pedidos urgentes"
    await _reply(chat_id, f"⚠️ *{total} {word}:*")

    for o in orders[:LIMIT]:
        await _send_order_card(chat_id, o)


async def _cmd_empacar(chat_id: int) -> None:
    orders = _pending_orders()
    if not orders:
        await _reply(chat_id, "✅ Nada que empacar por ahora\\.")
        return

    lines = ["📦 *Lista para empacar:*\n"]
    for o in orders:
        emoji = PRIORITY_EMOJI.get(o.shipping_priority.value, "📋")
        for item in o.items:
            sku = f" `{_esc(item.sku)}`" if item.sku else ""
            lines.append(f"{emoji} *×{item.quantity}* {_esc(item.title)}{sku}")

    await _reply(chat_id, "\n".join(lines))


async def _cmd_estado(chat_id: int, order_id_str: str) -> None:
    if not order_id_str.isdigit():
        await _reply(chat_id, "❌ Uso: `/estado 12345678`")
        return

    order = order_manager.orders.get(int(order_id_str))
    if not order:
        await _reply(chat_id, f"❌ Orden \\#{order_id_str} no encontrada\\.")
        return

    emoji = PRIORITY_EMOJI.get(order.shipping_priority.value, "📋")
    status = _esc(STATUS_LABELS.get(order.status, order.status))
    priority = _esc(PRIORITY_LABELS.get(order.shipping_priority.value, ""))
    items = "\n".join(
        f"  • {_esc(i.title)} ×{i.quantity}" + (f" \\(SKU: `{_esc(i.sku)}`\\)" if i.sku else "")
        for i in order.items
    )
    deadline = f"\n⏰ Límite: {_esc(order.shipping_deadline.strftime('%d/%m %H:%M'))}" if order.shipping_deadline else ""

    msg = (
        f"{emoji} *Orden \\#{order.order_id}*\n"
        f"\n"
        f"👤 *{_esc(order.buyer_nickname)}*\n"
        f"📋 {status}\n"
        f"💰 ${_esc(f'{order.total_amount:,.2f}')}\n"
        f"📦 {priority}"
        f"{deadline}\n"
        f"\n*Artículos:*\n{items}"
    )
    await _reply(chat_id, msg)


async def _cmd_ayuda(chat_id: int) -> None:
    msg = (
        "🤖 *Comandos disponibles:*\n\n"
        "/pedidos — todos los pedidos en curso\n"
        "/urgentes — solo los urgentes\n"
        "/empacar — lo que está listo para empacar\n"
        "/estado `<id>` — detalle de una orden\n"
        "/ayuda — esta lista"
    )
    await _reply(chat_id, msg)


# ------------------------------------------------------------------ #
#  Handler de callbacks (botones inline de notificaciones)            #
# ------------------------------------------------------------------ #

async def _handle_callback(callback_query: dict) -> None:
    query_id: str = callback_query["id"]
    chat_id: int = callback_query["message"]["chat"]["id"]
    data: str = callback_query.get("data", "")

    await _answer_callback(query_id)

    if not _is_authorized(chat_id):
        return

    if data.startswith("estado:"):
        order_id_str = data.split(":", 1)[1]
        await _cmd_estado(chat_id, order_id_str)
    elif data == "empacar":
        await _cmd_empacar(chat_id)
    elif data == "pedidos":
        await _cmd_pedidos(chat_id)
    elif data == "urgentes":
        await _cmd_urgentes(chat_id)


# ------------------------------------------------------------------ #
#  Endpoint que llama Telegram                                        #
# ------------------------------------------------------------------ #

COMMANDS = {
    "/pedidos":  _cmd_pedidos,
    "/urgentes": _cmd_urgentes,
    "/empacar":  _cmd_empacar,
    "/ayuda":    _cmd_ayuda,
}


@router.post("/updates")
async def telegram_updates(request: Request):
    """Recibe updates de Telegram: mensajes, comandos y callbacks de botones."""
    data = await request.json()

    if callback_query := data.get("callback_query"):
        await _handle_callback(callback_query)
        return {"ok": True}

    message = data.get("message") or data.get("edited_message")
    if not message:
        return {"ok": True}

    chat_id: int = message["chat"]["id"]
    text: str = message.get("text", "").strip()

    if not text.startswith("/"):
        return {"ok": True}

    if not _is_authorized(chat_id):
        await _reply(chat_id, "⛔ No autorizado\\.")
        return {"ok": True}

    cmd, arg = _parse_command(text)

    if cmd == "/estado":
        await _cmd_estado(chat_id, arg)
    elif cmd in COMMANDS:
        await COMMANDS[cmd](chat_id)
    else:
        await _reply(chat_id, "❓ Comando desconocido\\. Usa /ayuda para ver los disponibles\\.")

    return {"ok": True}
