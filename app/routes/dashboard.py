from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from app.meli_client import meli
from app.routes.ventas import _enrich_item, _format_date_short, _build_product_html
from app.ui import base_layout

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def dashboard():
    """Dashboard principal con resumen general."""
    total_pending = 0
    delayed_count = 0
    ready_count = 0
    shipped_count = 0
    total_amount = 0
    recent = []
    error_msg = ""

    try:
        data = await meli.get_pending_shipments()

        for item in data:
            shipment = item.get("shipment")
            if shipment and shipment.get("status") in ("delivered", "cancelled"):
                continue

            enriched = _enrich_item(item)
            total_pending += 1
            total_amount += enriched["total"]

            if enriched["category"] == "delayed":
                delayed_count += 1
            elif enriched["category"] == "ready":
                ready_count += 1
            elif enriched["category"] == "shipped":
                shipped_count += 1

            if len(recent) < 5:
                recent.append(enriched)
    except Exception as e:
        error_msg = str(e)

    # Recent rows
    recent_rows = ""
    recent_cards = ""
    for o in recent:
        is_delayed = o["category"] == "delayed"
        row_bg = ' style="background:var(--danger-bg);"' if is_delayed else ""
        card_border = "border-left:4px solid var(--danger);" if is_delayed else ""

        productos = _build_product_html(o["productos"])

        recent_rows += f"""<tr{row_bg}>
            <td><strong>#{o["order_id"]}</strong><br><small style="color:var(--text-muted);">{_format_date_short(o["date_created"])}</small></td>
            <td>{o["buyer"]}</td>
            <td style="max-width:250px;font-size:13px;">{productos}</td>
            <td><strong>${o["total"]:,.2f}</strong></td>
            <td><span class="badge {o["status_cls"]}">{o["status_label"]}</span></td>
            <td><span class="badge {o["tiempo_cls"]}">{o["tiempo_text"]}</span></td>
        </tr>"""

        recent_cards += f"""<div class="order-card" style="{card_border}">
            <div class="order-card-header">
                <div>
                    <div class="order-id">#{o["order_id"]}</div>
                    <div style="font-size:12px;color:var(--text-muted);">{_format_date_short(o["date_created"])} &middot; {o["buyer"]}</div>
                </div>
                <span class="badge {o["tiempo_cls"]}">{o["tiempo_text"]}</span>
            </div>
            <div class="order-card-products">{productos}</div>
            <div class="order-card-body">
                <div class="order-card-row">
                    <span class="label">Monto</span>
                    <strong>${o["total"]:,.2f}</strong>
                </div>
                <div class="order-card-row">
                    <span class="label">Estado</span>
                    <span class="badge {o["status_cls"]}">{o["status_label"]}</span>
                </div>
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
            <div class="stat-card danger">
                <div class="stat-label">Demorados</div>
                <div class="stat-value">{delayed_count}</div>
                <div class="stat-detail">Acción inmediata</div>
            </div>
            <div class="stat-card accent">
                <div class="stat-label">Por enviar</div>
                <div class="stat-value">{ready_count}</div>
                <div class="stat-detail">Listos para despachar</div>
            </div>
            <div class="stat-card success">
                <div class="stat-label">En camino</div>
                <div class="stat-value">{shipped_count}</div>
                <div class="stat-detail">Ya enviados</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Venta total</div>
                <div class="stat-value">${total_amount:,.0f}</div>
                <div class="stat-detail">MXN en {total_pending} pedidos</div>
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
                        <th>Plazo</th>
                    </tr></thead>
                    <tbody>{recent_rows}</tbody>
                </table>
            </div>
            <div class="order-cards" style="padding:12px;">{recent_cards}</div>'''
            if recent else
            '<div class="empty-state"><div class="icon">📦</div><p>No hay ventas pendientes</p></div>'}
        </div>
    """
    return HTMLResponse(content=base_layout("Dashboard", content, active="dashboard"))
