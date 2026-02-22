from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from app.meli_client import meli
from app.routes.ventas import _enrich_order, _format_date_short, _build_product_html, _sort_key
from app.ui import base_layout

router = APIRouter()


def _build_recent_card(o: dict) -> str:
    """Card resumida de pedido para el dashboard — clickable para ver detalle."""
    is_delayed = o["category"] == "delayed"
    border_map = {
        "delayed": "var(--danger)",
        "ready":   "var(--accent)",
        "shipped": "var(--success)",
        "pending": "var(--warning)",
    }
    border_color = border_map.get(o["category"], "var(--border-strong)")
    pulse_class = " pulse" if is_delayed else ""

    productos = _build_product_html(o["items"])

    # Label button
    ok_sub = ("ready_to_print", "printed", "handling_time_over")
    label_btn = ""
    if o.get("shipment_id") and o.get("shipping_substatus_raw") in ok_sub:
        label_btn = (
            f'<a href="/ventas/etiqueta/{o["shipment_id"]}"'
            f' target="_blank" class="btn btn-sm" style="font-size:11px;"'
            f' onclick="event.stopPropagation()">Imprimir etiqueta</a>'
        )

    shipment_id = o.get("shipment_id") or o["order_id"]

    return f"""
    <div class="order-card" style="border-left:4px solid {border_color};"
         onclick="openShipmentModal({shipment_id!r})" role="button" tabindex="0"
         onkeydown="if(event.key==='Enter')openShipmentModal({shipment_id!r})">
        <div class="order-card-header">
            <div>
                <div class="order-id">Pedido #{o["order_id"]}</div>
                <div style="font-size:12px;color:var(--text-muted);">
                    {_format_date_short(o["date_created"])} &middot; {o["buyer"]}
                </div>
            </div>
            <div style="display:flex;gap:5px;flex-wrap:wrap;align-items:center;">
                <span class="badge {o["status_cls"]}{pulse_class}">{o["status_label"]}</span>
                <span class="badge {o["tiempo_cls"]}">{o["tiempo_text"]}</span>
                {label_btn}
            </div>
        </div>
        <div>
            {productos}
            <div class="order-card-row" style="margin-top:6px;padding-top:6px;border-top:1px solid var(--border);">
                <span class="label">Total</span>
                <strong>${o["total"]:,.2f} {o["currency"]}</strong>
            </div>
        </div>
    </div>"""


@router.get("/", response_class=HTMLResponse)
async def dashboard():
    """Dashboard principal con resumen general."""
    delayed_count = 0
    ready_count = 0
    shipped_count = 0
    total_amount = 0.0
    orders = []
    error_msg = ""

    try:
        data = await meli.get_pending_shipments()

        for item in data:
            shipment = item.get("shipment")
            if shipment and shipment.get("status") in ("delivered", "cancelled"):
                continue
            enriched = _enrich_order(item)
            orders.append(enriched)
            total_amount += enriched["total"]

            cat = enriched["category"]
            if cat == "delayed":
                delayed_count += 1
            elif cat == "ready":
                ready_count += 1
            elif cat == "shipped":
                shipped_count += 1

        orders.sort(key=_sort_key)
    except Exception as e:
        error_msg = str(e)

    # Últimos 5 pedidos en el orden de prioridad
    recent = orders[:5]
    recent_cards = "".join(_build_recent_card(o) for o in recent)

    error_html = ""
    if error_msg:
        error_html = f"""
        <div class="error-banner">
            <div>
                <strong>Error al conectar con Mercado Libre</strong>
                <p>{error_msg}</p>
            </div>
        </div>"""

    n = len(orders)
    empty_state = '<div class="empty-state"><p>No hay ventas pendientes</p></div>'

    content = f"""
        <div class="page-header">
            <div>
                <h1 class="page-title">Dashboard</h1>
                <p class="page-subtitle">Resumen de tu operación en Mercado Libre</p>
            </div>
            <a href="/" class="btn" onclick="this.textContent='Cargando…';this.style.pointerEvents='none';">Actualizar</a>
        </div>

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
                <div class="stat-detail">MXN · {n} pedido{"s" if n != 1 else ""}</div>
            </div>
        </div>

        <div class="table-wrapper">
            <div class="table-header">
                <h2>Pedidos prioritarios</h2>
                <a href="/ventas/" class="btn btn-primary btn-sm">Ver todos</a>
            </div>
            <div style="padding:12px 14px;">
                {recent_cards if recent_cards else empty_state}
            </div>
        </div>
    """
    return HTMLResponse(content=base_layout("Dashboard", content, active="dashboard"))
