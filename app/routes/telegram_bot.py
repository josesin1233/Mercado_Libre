"""Comandos del bot de Telegram para consultar órdenes."""

import httpx
from fastapi import APIRouter, Request
from app.config import settings
from app.order_manager import order_manager

router = APIRouter()

PRIORITY_EMOJI = {
    "urgent": "⚠️",
    "high": "🔴",
    "normal": "🟡",
    "fulfilled": "✅",
}

STATUS_LABELS = {
    "confirmed": "Nueva",
    "payment_required": "Pago pendiente",
    "payment_in_process": "Pago en proceso",
    "paid": "Pagado",
    "shipped": "Enviado",
    "delivered": "Entregado",
    "cancelled": "Cancelado",
}


async def _reply(chat_id: int, text: str) -> None:
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(url, json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown",
        })


def _parse_command(text: str) -> tuple[str, str]:
    """Separa el comando del argumento. Elimina @BotName si viene de grupo."""
    parts = text.strip().split(None, 1)
    cmd = parts[0].split("@")[0].lower()
    arg = parts[1].strip() if len(parts) > 1 else ""
    return cmd, arg


def _is_authorized(chat_id: int) -> bool:
    return str(chat_id) == str(settings.TELEGRAM_CHAT_ID)


# ------------------------------------------------------------------ #
#  Handlers de comandos                                               #
# ------------------------------------------------------------------ #

async def _cmd_pedidos(chat_id: int) -> None:
    orders = order_manager.get_sorted_orders()
    if not orders:
        await _reply(chat_id, "✅ No hay pedidos pendientes.")
        return

    lines = [f"📦 *{len(orders)} pedido(s) pendiente(s):*\n"]
    for o in orders:
        emoji = PRIORITY_EMOJI.get(o.shipping_priority.value, "📋")
        status = STATUS_LABELS.get(o.status, o.status)
        items = ", ".join(f"{i.title} x{i.quantity}" for i in o.items)
        deadline = f" — ⏰ {o.shipping_deadline.strftime('%d/%m %H:%M')}" if o.shipping_deadline else ""
        lines.append(f"{emoji} *#{o.order_id}* — {status}{deadline}\n  {items}")

    await _reply(chat_id, "\n".join(lines))


async def _cmd_urgentes(chat_id: int) -> None:
    orders = order_manager.get_urgent_orders()
    if not orders:
        await _reply(chat_id, "✅ No hay pedidos urgentes.")
        return

    lines = [f"⚠️ *{len(orders)} pedido(s) urgente(s):*\n"]
    for o in orders:
        items = ", ".join(f"{i.title} x{i.quantity}" for i in o.items)
        deadline = f"⏰ Límite: {o.shipping_deadline.strftime('%d/%m %H:%M')}" if o.shipping_deadline else ""
        lines.append(f"*#{o.order_id}* — {deadline}\n  {items}")

    await _reply(chat_id, "\n".join(lines))


async def _cmd_empacar(chat_id: int) -> None:
    orders = order_manager.get_sorted_orders()
    if not orders:
        await _reply(chat_id, "✅ Nada que empacar.")
        return

    lines = ["📦 *Lista para empacar:*\n"]
    for o in orders:
        emoji = PRIORITY_EMOJI.get(o.shipping_priority.value, "📋")
        for item in o.items:
            sku = f" `{item.sku}`" if item.sku else ""
            lines.append(f"{emoji} *x{item.quantity}* {item.title}{sku}")

    await _reply(chat_id, "\n".join(lines))


async def _cmd_estado(chat_id: int, order_id_str: str) -> None:
    if not order_id_str.isdigit():
        await _reply(chat_id, "❌ Uso: `/estado 12345678`")
        return

    order = order_manager.orders.get(int(order_id_str))
    if not order:
        await _reply(chat_id, f"❌ Orden #{order_id_str} no encontrada en pedidos pendientes.")
        return

    emoji = PRIORITY_EMOJI.get(order.shipping_priority.value, "📋")
    status = STATUS_LABELS.get(order.status, order.status)
    items = "\n".join(
        f"  • {i.title} x{i.quantity}" + (f" (`{i.sku}`)" if i.sku else "")
        for i in order.items
    )
    deadline = f"\n⏰ Límite: {order.shipping_deadline.strftime('%d/%m %H:%M')}" if order.shipping_deadline else ""
    msg = (
        f"{emoji} *Orden #{order.order_id}*\n"
        f"👤 {order.buyer_nickname}\n"
        f"📋 Estado: {status}\n"
        f"💰 Total: ${order.total_amount:,.2f}{deadline}\n\n"
        f"*Productos:*\n{items}"
    )
    await _reply(chat_id, msg)


async def _cmd_ayuda(chat_id: int) -> None:
    msg = (
        "🤖 *Comandos disponibles:*\n\n"
        "/pedidos — todos los pedidos pendientes\n"
        "/urgentes — solo los pedidos urgentes\n"
        "/empacar — lista de productos a empacar\n"
        "/estado `<id>` — estado de un pedido específico\n"
        "/ayuda — esta lista"
    )
    await _reply(chat_id, msg)


# ------------------------------------------------------------------ #
#  Endpoint que llama Telegram                                        #
# ------------------------------------------------------------------ #

COMMANDS = {
    "/pedidos": _cmd_pedidos,
    "/urgentes": _cmd_urgentes,
    "/empacar": _cmd_empacar,
    "/ayuda": _cmd_ayuda,
}


@router.post("/updates")
async def telegram_updates(request: Request):
    """Recibe updates de Telegram (mensajes y comandos)."""
    data = await request.json()

    message = data.get("message") or data.get("edited_message")
    if not message:
        return {"ok": True}

    chat_id: int = message["chat"]["id"]
    text: str = message.get("text", "").strip()

    if not text.startswith("/"):
        return {"ok": True}

    if not _is_authorized(chat_id):
        await _reply(chat_id, "⛔ No autorizado.")
        return {"ok": True}

    cmd, arg = _parse_command(text)

    if cmd == "/estado":
        await _cmd_estado(chat_id, arg)
    elif cmd in COMMANDS:
        await COMMANDS[cmd](chat_id)
    else:
        await _reply(chat_id, "❓ Comando desconocido. Usa /ayuda para ver los disponibles.")

    return {"ok": True}
