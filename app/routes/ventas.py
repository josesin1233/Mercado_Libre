from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from datetime import datetime, timezone
from app.meli_client import meli
from app.ui import base_layout

router = APIRouter()


def _tiempo_restante(deadline_str: str | None) -> tuple[str, str]:
    """Retorna (texto, clase_badge)."""
    if not deadline_str:
        return "Sin fecha", "badge-neutral"
    try:
        deadline = datetime.fromisoformat(deadline_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        hours = (deadline - now).total_seconds() / 3600
        if hours < 0:
            return "VENCIDO", "badge-danger"
        elif hours < 24:
            return f"{int(hours)}h", "badge-danger"
        elif hours < 48:
            return f"{int(hours)}h", "badge-warning"
        else:
            return f"{int(hours / 24)}d", "badge-success"
    except Exception:
        return "—", "badge-neutral"


def _status_badge(shipment: dict | None) -> str:
    if not shipment:
        return '<span class="badge badge-neutral">Sin info</span>'
    status = shipment.get("status", "")
    mapping = {
        "pending": ("Pendiente", "badge-warning"),
        "ready_to_ship": ("Listo para enviar", "badge-accent"),
        "shipped": ("En camino", "badge-success"),
        "delivered": ("Entregado", "badge-success"),
        "not_delivered": ("No entregado", "badge-danger"),
        "cancelled": ("Cancelado", "badge-neutral"),
    }
    label, cls = mapping.get(status, (status, "badge-neutral"))
    return f'<span class="badge {cls}">{label}</span>'


@router.get("/", response_class=HTMLResponse)
async def ventas_pendientes():
    """Muestra las ventas pendientes de entregar."""
    try:
        data = await meli.get_pending_shipments()
    except Exception as e:
        error_content = f"""
            <h1 class="page-title">Ventas Pendientes</h1>
            <div style="background:var(--danger-bg);border:1px solid #fecaca;border-radius:var(--radius);padding:20px;margin-top:20px;">
                <strong style="color:#991b1b;">Error al obtener ventas</strong>
                <p style="color:#b91c1c;font-size:13px;margin-top:4px;">{e}</p>
                <p style="font-size:13px;margin-top:8px;">Verifica que ACCESS_TOKEN y USER_ID estén configurados.</p>
            </div>"""
        return HTMLResponse(content=base_layout("Error", error_content, active="ventas"), status_code=500)

    # Filtrar
    pending = []
    for item in data:
        shipment = item.get("shipment")
        if shipment and shipment.get("status") in ("delivered", "cancelled"):
            continue
        pending.append(item)

    total_amount = sum(item["order"].get("total_amount", 0) for item in pending)
    ready_count = len([p for p in pending if p.get("shipment") and p["shipment"].get("status") == "ready_to_ship"])

    # Build table rows and mobile cards
    rows = ""
    cards = ""
    for i, item in enumerate(pending, 1):
        order = item["order"]
        shipment = item.get("shipment")

        # Productos
        productos_html = ""
        productos_text = ""
        for oi in order.get("order_items", []):
            title = oi.get("item", {}).get("title", "?")
            qty = oi.get("quantity", 1)
            sku = oi.get("item", {}).get("seller_sku", "")
            sku_html = f' <span style="color:var(--text-muted);font-size:11px;">({sku})</span>' if sku else ""
            productos_html += f"<div>{title} <strong>x{qty}</strong>{sku_html}</div>"
            productos_text += f"<div>{title} x{qty}{sku_html}</div>"

        buyer = order.get("buyer", {}).get("nickname", "—")
        total = order.get("total_amount", 0)
        currency = order.get("currency_id", "MXN")

        # Fecha
        created = order.get("date_created", "")
        try:
            dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
            fecha = dt.strftime("%d/%m %H:%M")
        except Exception:
            fecha = "—"

        # Envío
        status_html = _status_badge(shipment)
        deadline = None
        if shipment:
            deadline = (
                shipment.get("shipping_option", {})
                .get("estimated_handling_limit", {})
                .get("date")
            )
        tiempo_text, tiempo_cls = _tiempo_restante(deadline)
        tiempo_badge = f'<span class="badge {tiempo_cls}">{tiempo_text}</span>'

        logistic = shipment.get("logistic_type", "—") if shipment else "—"
        order_id = order.get("id", "?")

        rows += f"""<tr>
            <td><strong>#{order_id}</strong><br><span style="font-size:12px;color:var(--text-muted);">{fecha}</span></td>
            <td>{buyer}</td>
            <td style="max-width:300px;font-size:13px;">{productos_html}</td>
            <td><strong>${total:,.2f}</strong><br><span style="font-size:11px;color:var(--text-muted);">{currency}</span></td>
            <td>{status_html}</td>
            <td><span style="font-size:12px;color:var(--text-muted);">{logistic}</span></td>
            <td>{tiempo_badge}</td>
        </tr>"""

        cards += f"""<div class="order-card">
            <div class="order-card-header">
                <div>
                    <div class="order-id">#{order_id}</div>
                    <div class="order-date">{fecha} &middot; {buyer}</div>
                </div>
                {tiempo_badge}
            </div>
            <div class="order-card-products">{productos_text}</div>
            <div class="order-card-body">
                <div class="order-card-row">
                    <span class="label">Monto</span>
                    <strong>${total:,.2f} {currency}</strong>
                </div>
                <div class="order-card-row">
                    <span class="label">Envío</span>
                    {status_html}
                </div>
                <div class="order-card-row">
                    <span class="label">Tipo</span>
                    <span>{logistic}</span>
                </div>
            </div>
        </div>"""

    table_html = ""
    if pending:
        table_html = f"""
        <div class="table-desktop">
            <table>
                <thead><tr>
                    <th>Orden</th>
                    <th>Comprador</th>
                    <th>Productos</th>
                    <th>Monto</th>
                    <th>Envío</th>
                    <th>Tipo</th>
                    <th>Plazo</th>
                </tr></thead>
                <tbody>{rows}</tbody>
            </table>
        </div>
        <div class="order-cards" style="padding:12px;">{cards}</div>"""
    else:
        table_html = '<div class="empty-state"><div class="icon">🎉</div><p>No hay ventas pendientes de entregar</p></div>'

    content = f"""
        <div style="display:flex;justify-content:space-between;align-items:start;flex-wrap:wrap;gap:8px;">
            <div>
                <h1 class="page-title">Ventas Pendientes</h1>
                <p class="page-subtitle">Órdenes pagadas que faltan por enviar</p>
            </div>
            <a href="/ventas/" class="btn" onclick="this.innerHTML='<span class=\\'spinner\\'></span> Cargando...';this.style.pointerEvents='none';">Actualizar</a>
        </div>

        <div class="stats">
            <div class="stat-card accent">
                <div class="stat-label">Total pendientes</div>
                <div class="stat-value">{len(pending)}</div>
            </div>
            <div class="stat-card warning">
                <div class="stat-label">Listas para enviar</div>
                <div class="stat-value">{ready_count}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Venta total</div>
                <div class="stat-value">${total_amount:,.0f}</div>
            </div>
        </div>

        <div class="table-wrapper">
            <div class="table-header">
                <h2>{len(pending)} orden{"es" if len(pending) != 1 else ""}</h2>
            </div>
            {table_html}
        </div>
    """
    return HTMLResponse(content=base_layout("Ventas Pendientes", content, active="ventas"))


@router.get("/api")
async def ventas_api():
    """Devuelve las ventas pendientes como JSON."""
    try:
        data = await meli.get_pending_shipments()
    except Exception as e:
        return {"error": str(e)}

    pending = []
    for item in data:
        shipment = item.get("shipment")
        if shipment and shipment.get("status") in ("delivered", "cancelled"):
            continue
        order = item["order"]
        pending.append({
            "order_id": order.get("id"),
            "buyer": order.get("buyer", {}).get("nickname"),
            "items": [
                {
                    "title": oi.get("item", {}).get("title"),
                    "quantity": oi.get("quantity"),
                    "sku": oi.get("item", {}).get("seller_sku"),
                }
                for oi in order.get("order_items", [])
            ],
            "total": order.get("total_amount"),
            "currency": order.get("currency_id"),
            "shipping_status": shipment.get("status") if shipment else None,
            "logistic_type": shipment.get("logistic_type") if shipment else None,
            "date_created": order.get("date_created"),
        })

    return {"total_pending": len(pending), "orders": pending}
