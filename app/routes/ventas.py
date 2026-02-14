from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from datetime import datetime, timezone
from collections import defaultdict
from app.meli_client import meli
from app.ui import base_layout

router = APIRouter()


# ── Helpers ──

def _parse_date(date_str: str | None) -> datetime | None:
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except Exception:
        return None


def _format_date(date_str: str | None) -> str:
    dt = _parse_date(date_str)
    if not dt:
        return "—"
    return dt.strftime("%d/%m/%Y %H:%M")


def _format_date_short(date_str: str | None) -> str:
    dt = _parse_date(date_str)
    if not dt:
        return "—"
    return dt.strftime("%d/%m %H:%M")


def _get_deadline(shipment: dict | None) -> str | None:
    """Extrae la fecha límite de despacho del shipment."""
    if not shipment:
        return None
    return (
        shipment.get("shipping_option", {})
        .get("estimated_handling_limit", {})
        .get("date")
    )


def _get_delivery_date(shipment: dict | None) -> str | None:
    """Extrae la fecha estimada de entrega."""
    if not shipment:
        return None
    return (
        shipment.get("shipping_option", {})
        .get("estimated_delivery_time", {})
        .get("date")
    )


def _classify_status(shipment: dict | None) -> tuple[str, str, str]:
    """
    Clasifica el estado real del envío cruzando status + substatus + deadline.
    Retorna (label, badge_class, category).
    Categories: 'delayed', 'ready', 'shipped', 'pending', 'other'
    """
    if not shipment:
        return "Sin info de envío", "badge-neutral", "pending"

    status = shipment.get("status", "")
    substatus = shipment.get("substatus") or ""

    # Si ya está entregado o cancelado, no debería llegar aquí pero por si acaso
    if status == "delivered":
        return "Entregado", "badge-success", "other"
    if status == "cancelled":
        return "Cancelado", "badge-neutral", "other"

    # Verificar si está demorado: deadline pasado y aún no está shipped
    deadline_str = _get_deadline(shipment)
    is_delayed = False
    if deadline_str and status in ("ready_to_ship", "pending"):
        deadline_dt = _parse_date(deadline_str)
        if deadline_dt and datetime.now(timezone.utc) > deadline_dt:
            is_delayed = True

    if status == "shipped":
        # Substatuses de shipped
        sub_labels = {
            "in_hub": "En centro de distribución",
            "waiting_for_withdrawal": "Esperando retiro",
            "out_for_delivery": "En reparto",
            "soon_deliver": "Por entregar",
            "delivered": "Entregado",
        }
        label = sub_labels.get(substatus, "En camino")
        return label, "badge-success", "shipped"

    if status == "ready_to_ship":
        if is_delayed:
            sub_labels = {
                "ready_to_print": "DEMORADO - Imprimir etiqueta",
                "printed": "DEMORADO - Despachar",
                "ready_for_pkl": "DEMORADO - Preparar",
                "invoice_pending": "DEMORADO - Factura pendiente",
            }
            label = sub_labels.get(substatus, "DEMORADO")
            return label, "badge-danger", "delayed"
        else:
            sub_labels = {
                "ready_to_print": "Imprimir etiqueta",
                "printed": "Etiqueta impresa",
                "ready_for_pkl": "Preparar paquete",
                "invoice_pending": "Factura pendiente",
            }
            label = sub_labels.get(substatus, "Listo para enviar")
            return label, "badge-accent", "ready"

    if status == "pending":
        if is_delayed:
            return "DEMORADO - Pendiente", "badge-danger", "delayed"
        return "Pendiente", "badge-warning", "pending"

    if status == "not_delivered":
        return "No entregado", "badge-danger", "delayed"

    return f"{status} ({substatus})" if substatus else status, "badge-neutral", "other"


def _tiempo_restante(deadline_str: str | None) -> tuple[str, str]:
    """Retorna (texto, badge_class)."""
    if not deadline_str:
        return "Sin fecha", "badge-neutral"
    dt = _parse_date(deadline_str)
    if not dt:
        return "—", "badge-neutral"
    now = datetime.now(timezone.utc)
    hours = (dt - now).total_seconds() / 3600
    if hours < 0:
        abs_h = abs(int(hours))
        if abs_h >= 24:
            return f"Hace {abs_h // 24}d", "badge-danger"
        return f"Hace {abs_h}h", "badge-danger"
    elif hours < 24:
        return f"{int(hours)}h", "badge-warning"
    elif hours < 48:
        return f"{int(hours)}h", "badge-warning"
    else:
        return f"{int(hours / 24)}d", "badge-success"


def _enrich_item(item: dict) -> dict:
    """Enriquece un item con datos procesados."""
    order = item["order"]
    shipment = item.get("shipment")

    deadline_str = _get_deadline(shipment)
    delivery_str = _get_delivery_date(shipment)
    status_label, status_cls, category = _classify_status(shipment)
    tiempo_text, tiempo_cls = _tiempo_restante(deadline_str)

    return {
        **item,
        "order_id": order.get("id", "?"),
        "buyer": order.get("buyer", {}).get("nickname", "—"),
        "buyer_id": order.get("buyer", {}).get("id"),
        "total": order.get("total_amount", 0),
        "currency": order.get("currency_id", "MXN"),
        "date_created": order.get("date_created", ""),
        "deadline_str": deadline_str,
        "delivery_str": delivery_str,
        "status_label": status_label,
        "status_cls": status_cls,
        "category": category,
        "tiempo_text": tiempo_text,
        "tiempo_cls": tiempo_cls,
        "logistic": shipment.get("logistic_type", "—") if shipment else "—",
        "productos": [
            {
                "title": oi.get("item", {}).get("title", "?"),
                "qty": oi.get("quantity", 1),
                "sku": oi.get("item", {}).get("seller_sku", ""),
            }
            for oi in order.get("order_items", [])
        ],
    }


# ── HTML builders ──

def _build_product_html(productos: list[dict]) -> str:
    html = ""
    for p in productos:
        sku = f' <span style="color:var(--text-muted);font-size:11px;">({p["sku"]})</span>' if p["sku"] else ""
        html += f'<div>{p["title"]} <strong>x{p["qty"]}</strong>{sku}</div>'
    return html


def _build_row(item: dict, is_delayed: bool) -> str:
    row_style = ' style="background:var(--danger-bg);"' if is_delayed else ""
    productos = _build_product_html(item["productos"])

    return f"""<tr{row_style}>
        <td>
            <strong>#{item["order_id"]}</strong><br>
            <span style="font-size:12px;color:var(--text-muted);">{_format_date_short(item["date_created"])}</span>
        </td>
        <td>{item["buyer"]}</td>
        <td style="max-width:280px;font-size:13px;">{productos}</td>
        <td><strong>${item["total"]:,.2f}</strong></td>
        <td><span class="badge {item["status_cls"]}">{item["status_label"]}</span></td>
        <td>{_format_date_short(item["deadline_str"])}</td>
        <td><span class="badge {item["tiempo_cls"]}">{item["tiempo_text"]}</span></td>
    </tr>"""


def _build_card(item: dict, is_delayed: bool) -> str:
    border = "border-left:4px solid var(--danger);" if is_delayed else ""
    bg = "background:var(--danger-bg);" if is_delayed else ""
    productos = _build_product_html(item["productos"])

    return f"""<div class="order-card" style="{border}{bg}">
        <div class="order-card-header">
            <div>
                <div class="order-id">#{item["order_id"]}</div>
                <div class="order-date">{_format_date_short(item["date_created"])} &middot; {item["buyer"]}</div>
            </div>
            <span class="badge {item["tiempo_cls"]}">{item["tiempo_text"]}</span>
        </div>
        <div class="order-card-products">{productos}</div>
        <div class="order-card-body">
            <div class="order-card-row">
                <span class="label">Monto</span>
                <strong>${item["total"]:,.2f} {item["currency"]}</strong>
            </div>
            <div class="order-card-row">
                <span class="label">Estado</span>
                <span class="badge {item["status_cls"]}">{item["status_label"]}</span>
            </div>
            <div class="order-card-row">
                <span class="label">Fecha envío</span>
                <span>{_format_date_short(item["deadline_str"])}</span>
            </div>
            <div class="order-card-row">
                <span class="label">Tipo</span>
                <span>{item["logistic"]}</span>
            </div>
        </div>
    </div>"""


def _build_section(title: str, icon: str, items: list[dict], section_cls: str) -> str:
    """Construye una sección completa (tabla desktop + cards mobile)."""
    if not items:
        return ""

    is_delayed = section_cls == "delayed"

    # Agrupar por comprador
    groups: dict[str, list[dict]] = defaultdict(list)
    for item in items:
        groups[item["buyer"]].append(item)

    # Ordenar grupos por deadline más temprano
    def group_sort_key(buyer_items: tuple[str, list[dict]]) -> datetime:
        deadlines = [_parse_date(i["deadline_str"]) for i in buyer_items[1] if i["deadline_str"]]
        return min(deadlines) if deadlines else datetime.max.replace(tzinfo=timezone.utc)

    sorted_groups = sorted(groups.items(), key=group_sort_key)

    rows = ""
    cards = ""

    for buyer, buyer_items in sorted_groups:
        is_group = len(buyer_items) > 1

        if is_group:
            group_total = sum(i["total"] for i in buyer_items)
            group_count = len(buyer_items)
            rows += f"""<tr style="background:var(--accent-soft);">
                <td colspan="7" style="padding:8px 20px;font-size:13px;">
                    <strong>{buyer}</strong> &mdash; {group_count} pedidos &mdash; Total: <strong>${group_total:,.2f}</strong>
                </td>
            </tr>"""
            cards += f"""<div style="background:var(--accent-soft);padding:10px 16px;border-radius:var(--radius-sm);margin:16px 0 4px 0;font-size:13px;">
                <strong>{buyer}</strong> &mdash; {group_count} pedidos &mdash; ${group_total:,.2f}
            </div>"""

        for item in buyer_items:
            rows += _build_row(item, is_delayed)
            cards += _build_card(item, is_delayed)

    border_color = {
        "delayed": "var(--danger)",
        "ready": "var(--accent)",
        "shipped": "var(--success)",
        "pending": "var(--warning)",
    }.get(section_cls, "var(--border)")

    count = len(items)

    return f"""
    <div class="table-wrapper" style="margin-bottom:24px;border-top:3px solid {border_color};">
        <div class="table-header">
            <h2>{icon} {title} <span style="font-weight:400;color:var(--text-muted);font-size:14px;">({count})</span></h2>
        </div>
        <div class="table-desktop">
            <table>
                <thead><tr>
                    <th>Orden</th>
                    <th>Comprador</th>
                    <th>Productos</th>
                    <th>Monto</th>
                    <th>Estado</th>
                    <th>Fecha envío</th>
                    <th>Plazo</th>
                </tr></thead>
                <tbody>{rows}</tbody>
            </table>
        </div>
        <div class="order-cards" style="padding:12px;">{cards}</div>
    </div>"""


# ── Routes ──

@router.get("/", response_class=HTMLResponse)
async def ventas_pendientes():
    """Muestra las ventas pendientes separadas por estado."""
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

    # Filtrar entregados/cancelados y enriquecer
    items = []
    for item in data:
        shipment = item.get("shipment")
        if shipment and shipment.get("status") in ("delivered", "cancelled"):
            continue
        items.append(_enrich_item(item))

    # Separar por categoría
    delayed = [i for i in items if i["category"] == "delayed"]
    ready = [i for i in items if i["category"] == "ready"]
    shipped = [i for i in items if i["category"] == "shipped"]
    pending = [i for i in items if i["category"] == "pending"]

    total_amount = sum(i["total"] for i in items)

    # Stats
    content = f"""
        <div style="display:flex;justify-content:space-between;align-items:start;flex-wrap:wrap;gap:8px;">
            <div>
                <h1 class="page-title">Ventas Pendientes</h1>
                <p class="page-subtitle">Ordenadas por fecha de envío, agrupadas por comprador</p>
            </div>
            <a href="/ventas/" class="btn" onclick="this.innerHTML='Cargando...';this.style.pointerEvents='none';">Actualizar</a>
        </div>

        <div class="stats">
            <div class="stat-card danger">
                <div class="stat-label">Demorados</div>
                <div class="stat-value">{len(delayed)}</div>
                <div class="stat-detail">Requieren acción inmediata</div>
            </div>
            <div class="stat-card accent">
                <div class="stat-label">Por enviar</div>
                <div class="stat-value">{len(ready)}</div>
                <div class="stat-detail">Listos para despachar</div>
            </div>
            <div class="stat-card success">
                <div class="stat-label">En camino</div>
                <div class="stat-value">{len(shipped)}</div>
                <div class="stat-detail">Ya enviados</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Venta total</div>
                <div class="stat-value">${total_amount:,.0f}</div>
                <div class="stat-detail">MXN en {len(items)} orden{"es" if len(items) != 1 else ""}</div>
            </div>
        </div>

        {_build_section("Demorados", "🔴", delayed, "delayed")}
        {_build_section("Listos para enviar", "📦", ready, "ready")}
        {_build_section("Pendientes", "⏳", pending, "pending")}
        {_build_section("En camino", "🚚", shipped, "shipped")}

        {"" if items else '<div class="empty-state"><div class="icon">🎉</div><p>No hay ventas pendientes</p></div>'}
    """
    return HTMLResponse(content=base_layout("Ventas Pendientes", content, active="ventas"))


@router.get("/debug")
async def ventas_debug():
    """Muestra datos crudos de ML para debugging."""
    try:
        data = await meli.get_pending_shipments()
    except Exception as e:
        return {"error": str(e)}

    results = []
    for item in data:
        shipment = item.get("shipment")
        order = item["order"]
        results.append({
            "order_id": order.get("id"),
            "order_status": order.get("status"),
            "buyer": order.get("buyer", {}).get("nickname"),
            "shipping_status": shipment.get("status") if shipment else None,
            "shipping_substatus": shipment.get("substatus") if shipment else None,
            "logistic_type": shipment.get("logistic_type") if shipment else None,
            "handling_limit": _get_deadline(shipment),
            "delivery_date": _get_delivery_date(shipment),
            "date_created": order.get("date_created"),
        })
    return {"total": len(results), "orders": results}


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
        enriched = _enrich_item(item)
        pending.append({
            "order_id": enriched["order_id"],
            "buyer": enriched["buyer"],
            "productos": enriched["productos"],
            "total": enriched["total"],
            "currency": enriched["currency"],
            "status": enriched["status_label"],
            "category": enriched["category"],
            "deadline": enriched["deadline_str"],
            "delivery_date": enriched["delivery_str"],
            "logistic_type": enriched["logistic"],
            "date_created": enriched["date_created"],
        })

    return {"total_pending": len(pending), "orders": pending}
