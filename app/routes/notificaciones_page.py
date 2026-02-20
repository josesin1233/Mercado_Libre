from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from app.order_manager import order_manager
from app.models import ShippingPriority
from app.ui import base_layout

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def notificaciones_page():
    """Página de notificaciones y alertas."""
    orders = order_manager.get_sorted_orders()
    urgent = order_manager.get_urgent_orders()

    # ── Packing list ──────────────────────────────────────────────────────────
    pack_items = ""
    for order in orders:
        for item in order.items:
            # Classify badge by priority (using enum comparison, not .value)
            if order.shipping_priority == ShippingPriority.URGENT:
                priority_cls = "badge-danger"
            elif order.shipping_priority == ShippingPriority.HIGH:
                priority_cls = "badge-warning"
            else:
                priority_cls = "badge-neutral"

            sku_html = (
                f'<span style="font-family:monospace;font-size:11px;color:var(--text-muted);">'
                f'SKU: {item.sku}</span>'
                if item.sku else ""
            )

            pack_items += f"""
            <div class="order-card" style="cursor:default;transform:none;">
                <div class="order-card-header">
                    <div>
                        <div class="order-id">{item.title}</div>
                        <div style="font-size:12px;color:var(--text-muted);margin-top:2px;">
                            Orden #{order.order_id}{f' &middot; {sku_html}' if item.sku else ''}
                        </div>
                    </div>
                    <span class="badge {priority_cls}">x{item.quantity}</span>
                </div>
            </div>"""

    # ── Product frequency ─────────────────────────────────────────────────────
    product_count: dict[str, dict] = {}
    for order in orders:
        for item in order.items:
            key = item.item_id
            if key not in product_count:
                product_count[key] = {"title": item.title, "sku": item.sku, "total": 0}
            product_count[key]["total"] += item.quantity

    sorted_products = sorted(product_count.values(), key=lambda x: x["total"], reverse=True)

    stock_rows = ""
    for p in sorted_products:
        sku_text = (
            f'<br><span style="color:var(--text-muted);font-size:11px;font-family:monospace;">{p["sku"]}</span>'
            if p["sku"] else ""
        )
        bar_pct = min(100, int(p["total"] / max(1, max(x["total"] for x in sorted_products)) * 100))
        stock_rows += f"""<tr>
            <td>
                {p["title"]}{sku_text}
                <div style="height:3px;background:var(--accent-soft);border-radius:2px;margin-top:6px;">
                    <div style="height:3px;width:{bar_pct}%;background:var(--accent);border-radius:2px;"></div>
                </div>
            </td>
            <td style="text-align:right;font-weight:700;color:var(--accent);font-size:16px;">
                {p["total"]}
            </td>
        </tr>"""

    total_items = sum(item.quantity for o in orders for item in o.items)
    urgent_cls = "danger" if urgent else "success"

    content = f"""
        <div class="page-header">
            <div>
                <h1 class="page-title">Notificaciones</h1>
                <p class="page-subtitle">Alertas, lista de empaque y productos más vendidos</p>
            </div>
        </div>

        <div class="stats">
            <div class="stat-card {urgent_cls}">
                <div class="stat-label">Urgentes</div>
                <div class="stat-value">{len(urgent)}</div>
                <div class="stat-detail">{"Atención inmediata" if urgent else "Todo bajo control"}</div>
            </div>
            <div class="stat-card accent">
                <div class="stat-label">Pendientes</div>
                <div class="stat-value">{len(orders)}</div>
                <div class="stat-detail">Órdenes activas</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">A empacar</div>
                <div class="stat-value">{total_items}</div>
                <div class="stat-detail">Unidades totales</div>
            </div>
        </div>

        <div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(340px, 1fr));gap:20px;">
            <div class="table-wrapper">
                <div class="table-header">
                    <h2>Lista de empaque</h2>
                    <span class="badge badge-accent">{total_items} unidades</span>
                </div>
                <div style="padding:12px 14px;">
                    {pack_items if pack_items else '<div class="empty-state"><span class="icon">📦</span><p>Nada que empacar</p></div>'}
                </div>
            </div>

            <div class="table-wrapper">
                <div class="table-header">
                    <h2>Productos más vendidos</h2>
                    <span class="badge badge-neutral">{len(sorted_products)} SKUs</span>
                </div>
                {
                    f'<table><thead><tr><th>Producto</th><th style="text-align:right;">Unidades</th></tr></thead><tbody>{stock_rows}</tbody></table>'
                    if stock_rows
                    else '<div class="empty-state"><span class="icon">📊</span><p>Sin datos aún</p></div>'
                }
            </div>
        </div>
    """
    return HTMLResponse(content=base_layout("Notificaciones", content, active="notificaciones"))
