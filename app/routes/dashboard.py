from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from app.meli_client import meli
from app.routes.ventas import _enrich_order, _format_date_short, _build_product_html, _sort_key
from app.ui import base_layout

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def dashboard():
    """Dashboard principal con resumen general."""
    delayed_count = 0
    ready_count = 0
    shipped_count = 0
    total_amount = 0
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

            if enriched["category"] == "delayed":
                delayed_count += 1
            elif enriched["category"] == "ready":
                ready_count += 1
            elif enriched["category"] == "shipped":
                shipped_count += 1

        orders.sort(key=_sort_key)
    except Exception as e:
        error_msg = str(e)

    # Recent orders (max 5)
    recent = orders[:5]

    recent_cards = ""
    for o in recent:
        is_delayed = o["category"] == "delayed"
        border = "border-left:4px solid var(--danger);" if is_delayed else ""
        bg_style = "background:var(--danger-bg);" if is_delayed else ""
        productos = _build_product_html(o["items"])

        label_btn = ""
        if o.get("shipment_id") and o.get("shipping_substatus_raw") in ("ready_to_print", "printed", "handling_time_over"):
            label_btn = f'<a href="https://www.mercadolibre.com.mx/envios/{o["shipment_id"]}/ver_etiqueta" target="_blank" style="font-size:12px;padding:3px 8px;background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);color:var(--text);text-decoration:none;">🖨️ Etiqueta</a>'

        main_thumb = next((i.get("thumbnail", "") for i in o["items"] if i.get("thumbnail")), "")
        thumb_html = f'<img src="{main_thumb}" style="width:56px;height:56px;object-fit:contain;border-radius:8px;border:1px solid var(--border);background:#fff;flex-shrink:0;" alt="">' if main_thumb else ""

        recent_cards += f"""<div class="order-card" style="{border}{bg_style}">
            <div class="order-card-header">
                <div>
                    <div class="order-id">Pedido #{o["order_id"]}</div>
                    <div style="font-size:12px;color:var(--text-muted);">{_format_date_short(o["date_created"])} &middot; {o["buyer"]}</div>
                </div>
                <div style="display:flex;gap:4px;flex-wrap:wrap;align-items:center;">
                    <span class="badge {o["status_cls"]}">{o["status_label"]}</span>
                    <span class="badge {o["tiempo_cls"]}">{o["tiempo_text"]}</span>
                    {label_btn}
                </div>
            </div>
            <div style="display:flex;gap:12px;align-items:flex-start;">
                <div style="flex:1;">
                    <div class="order-card-products">{productos}</div>
                    <div class="order-card-row">
                        <span class="label">Total</span>
                        <strong>${o["total"]:,.2f}</strong>
                    </div>
                </div>
                {thumb_html}
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
                <div class="stat-detail">MXN en {len(orders)} pedidos</div>
            </div>
        </div>

        <div class="table-wrapper">
            <div class="table-header">
                <h2>Pedidos recientes</h2>
                <a href="/ventas/" class="btn btn-primary">Ver todos</a>
            </div>
            <div style="padding:12px;">
                {recent_cards if recent_cards else '<div class="empty-state"><div class="icon">📦</div><p>No hay ventas pendientes</p></div>'}
            </div>
        </div>
    """
    return HTMLResponse(content=base_layout("Dashboard", content, active="dashboard"))
