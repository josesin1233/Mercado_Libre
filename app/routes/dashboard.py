from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from app.meli_client import meli
from app.ui import base_layout

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def dashboard():
    """Dashboard principal con resumen general."""

    # Intentar cargar datos de ML
    total_pending = 0
    total_ready = 0
    total_shipped = 0
    total_amount = 0
    recent_orders = []
    error_msg = ""

    try:
        data = await meli.get_pending_shipments()

        for item in data:
            order = item["order"]
            shipment = item.get("shipment")
            status = shipment.get("status", "") if shipment else ""

            if status in ("delivered", "cancelled"):
                continue

            total_pending += 1
            total_amount += order.get("total_amount", 0)

            if status == "ready_to_ship":
                total_ready += 1
            elif status == "shipped":
                total_shipped += 1

            if len(recent_orders) < 5:
                productos = ", ".join(
                    f'{oi.get("item", {}).get("title", "?")} x{oi.get("quantity", 1)}'
                    for oi in order.get("order_items", [])
                )
                recent_orders.append({
                    "id": order.get("id"),
                    "buyer": order.get("buyer", {}).get("nickname", "—"),
                    "productos": productos,
                    "total": order.get("total_amount", 0),
                    "currency": order.get("currency_id", "MXN"),
                    "status": status,
                })
    except Exception as e:
        error_msg = str(e)

    # Status badges
    def status_badge(s: str) -> str:
        m = {
            "pending": ('<span class="badge badge-warning">Pendiente</span>'),
            "ready_to_ship": ('<span class="badge badge-accent">Listo para enviar</span>'),
            "shipped": ('<span class="badge badge-success">En camino</span>'),
        }
        return m.get(s, f'<span class="badge badge-neutral">{s}</span>')

    # Recent orders rows
    recent_rows = ""
    recent_cards = ""
    for o in recent_orders:
        recent_rows += f"""<tr>
            <td><strong>#{o["id"]}</strong></td>
            <td>{o["buyer"]}</td>
            <td style="max-width:300px;">{o["productos"]}</td>
            <td>${o["total"]:,.2f}</td>
            <td>{status_badge(o["status"])}</td>
        </tr>"""
        recent_cards += f"""<div class="order-card">
            <div class="order-card-header">
                <div>
                    <div class="order-id">#{o["id"]}</div>
                    <div style="font-size:12px;color:var(--text-muted);margin-top:2px;">{o["buyer"]}</div>
                </div>
                {status_badge(o["status"])}
            </div>
            <div class="order-card-products"><div>{o["productos"]}</div></div>
            <div class="order-card-row">
                <span class="label">Total</span>
                <strong>${o["total"]:,.2f} {o["currency"]}</strong>
            </div>
        </div>"""

    error_html = ""
    if error_msg:
        error_html = f"""<div style="background:var(--danger-bg);border:1px solid #fecaca;border-radius:var(--radius);padding:16px;margin-bottom:24px;">
            <strong style="color:#991b1b;">Error al conectar con Mercado Libre</strong>
            <p style="color:#b91c1c;font-size:13px;margin-top:4px;">{error_msg}</p>
        </div>"""

    content = f"""
        <h1 class="page-title">Dashboard</h1>
        <p class="page-subtitle">Resumen de tu operación en Mercado Libre</p>

        {error_html}

        <div class="stats">
            <div class="stat-card accent">
                <div class="stat-label">Pendientes</div>
                <div class="stat-value">{total_pending}</div>
                <div class="stat-detail">Órdenes por gestionar</div>
            </div>
            <div class="stat-card warning">
                <div class="stat-label">Listas para enviar</div>
                <div class="stat-value">{total_ready}</div>
                <div class="stat-detail">Preparar paquete</div>
            </div>
            <div class="stat-card success">
                <div class="stat-label">En camino</div>
                <div class="stat-value">{total_shipped}</div>
                <div class="stat-detail">Ya enviadas</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Venta total</div>
                <div class="stat-value">${total_amount:,.0f}</div>
                <div class="stat-detail">MXN pendiente</div>
            </div>
        </div>

        <div class="table-wrapper">
            <div class="table-header">
                <h2>Ventas recientes</h2>
                <a href="/ventas/" class="btn btn-primary">Ver todas</a>
            </div>
            {f'''<div class="table-desktop">
                <table>
                    <thead><tr>
                        <th>Orden</th>
                        <th>Comprador</th>
                        <th>Productos</th>
                        <th>Monto</th>
                        <th>Estado</th>
                    </tr></thead>
                    <tbody>{recent_rows}</tbody>
                </table>
            </div>
            <div class="order-cards" style="padding:12px;">{recent_cards}</div>'''
            if recent_orders else
            '<div class="empty-state"><div class="icon">📦</div><p>No hay ventas pendientes</p></div>'}
        </div>
    """
    return HTMLResponse(content=base_layout("Dashboard", content, active="dashboard"))
