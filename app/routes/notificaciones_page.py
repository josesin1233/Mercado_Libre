from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from app.order_manager import order_manager
from app.ui import base_layout

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def notificaciones_page():
    """Página de notificaciones y alertas."""
    orders = order_manager.get_sorted_orders()
    urgent = order_manager.get_urgent_orders()

    # Packing list
    pack_items = ""
    for order in orders:
        for item in order.items:
            priority_cls = "badge-danger" if order.shipping_priority.value <= 1 else "badge-warning" if order.shipping_priority.value == 2 else "badge-neutral"
            pack_items += f"""<div class="order-card">
                <div class="order-card-header">
                    <div>
                        <div class="order-id">{item.title}</div>
                        <div style="font-size:12px;color:var(--text-muted);">Orden #{order.order_id}{f" &middot; SKU: {item.sku}" if item.sku else ""}</div>
                    </div>
                    <span class="badge {priority_cls}">x{item.quantity}</span>
                </div>
            </div>"""

    # Product frequency
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
        sku_text = f'<span style="color:var(--text-muted);font-size:12px;">{p["sku"]}</span>' if p["sku"] else ""
        stock_rows += f"""<tr>
            <td>{p["title"]}<br>{sku_text}</td>
            <td><strong>{p["total"]}</strong></td>
        </tr>"""

    content = f"""
        <h1 class="page-title">Notificaciones</h1>
        <p class="page-subtitle">Alertas, lista de empaque y productos más vendidos</p>

        <div class="stats">
            <div class="stat-card {"danger" if urgent else "success"}">
                <div class="stat-label">Urgentes</div>
                <div class="stat-value">{len(urgent)}</div>
            </div>
            <div class="stat-card accent">
                <div class="stat-label">Pendientes</div>
                <div class="stat-value">{len(orders)}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Productos a empacar</div>
                <div class="stat-value">{sum(item.quantity for o in orders for item in o.items)}</div>
            </div>
        </div>

        <div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(350px, 1fr));gap:20px;">
            <div class="table-wrapper">
                <div class="table-header">
                    <h2>Lista de empaque</h2>
                </div>
                <div style="padding:12px;">
                    {pack_items if pack_items else '<div class="empty-state"><div class="icon">📦</div><p>Nada que empacar</p></div>'}
                </div>
            </div>

            <div class="table-wrapper">
                <div class="table-header">
                    <h2>Productos más vendidos</h2>
                </div>
                {f'<table><thead><tr><th>Producto</th><th>Unidades</th></tr></thead><tbody>{stock_rows}</tbody></table>' if stock_rows else '<div class="empty-state"><div class="icon">📊</div><p>Sin datos aún</p></div>'}
            </div>
        </div>
    """
    return HTMLResponse(content=base_layout("Notificaciones", content, active="notificaciones"))
