from fastapi import APIRouter
from fastapi.responses import HTMLResponse, Response, JSONResponse
from datetime import datetime, timezone
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


def _format_date_short(date_str: str | None) -> str:
    dt = _parse_date(date_str)
    if not dt:
        return "—"
    return dt.strftime("%d/%m %H:%M")


def _get_deadline(shipment: dict | None) -> str | None:
    """Busca la fecha límite de despacho probando varias rutas del API de ML."""
    if not shipment:
        return None
    so = shipment.get("shipping_option") or {}
    # Ruta 1: estimated_delivery_limit (última fecha para despachar a tiempo)
    d = (so.get("estimated_delivery_limit") or {}).get("date")
    if d:
        return d
    # Ruta 2: estimated_handling_limit dentro de shipping_option
    d = (so.get("estimated_handling_limit") or {}).get("date")
    if d:
        return d
    # Ruta 3: estimated_handling_limit directo
    ehl = shipment.get("estimated_handling_limit")
    if isinstance(ehl, dict):
        d = ehl.get("date")
        if d:
            return d
    elif isinstance(ehl, str):
        return ehl
    # Ruta 4: estimated_delivery_final como último recurso
    d = (so.get("estimated_delivery_final") or {}).get("date")
    return d


def _get_delivery_date(shipment: dict | None) -> str | None:
    """Busca la fecha estimada de entrega."""
    if not shipment:
        return None
    d = (
        shipment.get("shipping_option", {})
        .get("estimated_delivery_time", {})
        .get("date")
    )
    if d:
        return d
    edt = shipment.get("estimated_delivery_time")
    if isinstance(edt, dict):
        return edt.get("date")
    elif isinstance(edt, str):
        return edt
    # Ruta 3: estimated_delivery_final
    d = (
        shipment.get("shipping_option", {})
        .get("estimated_delivery_final", {})
        .get("date")
    )
    return d


def _get_ship_by_date(shipment: dict | None) -> str | None:
    """Obtiene la mejor fecha disponible para 'cuándo debería enviarse'.
    Prioriza: handling_limit > date_first_printed > last_updated."""
    deadline = _get_deadline(shipment)
    if deadline:
        return deadline
    delivery = _get_delivery_date(shipment)
    if delivery:
        return delivery
    if not shipment:
        return None
    return shipment.get("date_created")


def _classify_status(shipment: dict | None, deadline_str: str | None) -> tuple[str, str, str]:
    """
    Clasifica el estado real cruzando status + substatus + deadline.
    Retorna (label, badge_class, category).
    Categories: 'delayed', 'ready', 'shipped', 'pending', 'other'
    """
    if not shipment:
        return "Sin info de envío", "badge-neutral", "pending"

    status = shipment.get("status", "")
    substatus = shipment.get("substatus") or ""

    if status == "delivered":
        return "Entregado", "badge-success", "other"
    if status == "cancelled":
        return "Cancelado", "badge-neutral", "other"

    # ¿Está demorado? Por substatus explícito o deadline pasado
    is_delayed = substatus == "handling_time_over"
    if not is_delayed and deadline_str and status in ("ready_to_ship", "pending"):
        deadline_dt = _parse_date(deadline_str)
        if deadline_dt and datetime.now(timezone.utc) > deadline_dt:
            is_delayed = True

    if status == "shipped":
        sub_labels = {
            "in_hub": "En centro de distribución",
            "waiting_for_withdrawal": "Esperando retiro",
            "out_for_delivery": "En reparto",
            "soon_deliver": "Por entregar",
        }
        return sub_labels.get(substatus, "En camino"), "badge-success", "shipped"

    if status == "ready_to_ship":
        if is_delayed:
            sub_labels = {
                "ready_to_print": "DEMORADO - Imprimir etiqueta",
                "printed": "DEMORADO - Despachar",
            }
            return sub_labels.get(substatus, "DEMORADO"), "badge-danger", "delayed"
        else:
            sub_labels = {
                "ready_to_print": "Imprimir etiqueta",
                "printed": "Etiqueta impresa",
            }
            return sub_labels.get(substatus, "Listo para enviar"), "badge-accent", "ready"

    if status == "pending":
        if is_delayed:
            return "DEMORADO", "badge-danger", "delayed"
        return "Pendiente", "badge-warning", "pending"

    if status == "not_delivered":
        return "No entregado", "badge-danger", "delayed"

    return f"{status}" + (f" ({substatus})" if substatus else ""), "badge-neutral", "other"


def _tiempo_restante(deadline_str: str | None) -> tuple[str, str]:
    if not deadline_str:
        return "—", "badge-neutral"
    dt = _parse_date(deadline_str)
    if not dt:
        return "—", "badge-neutral"
    now = datetime.now(timezone.utc)
    hours = (dt - now).total_seconds() / 3600
    if hours < 0:
        abs_h = abs(int(hours))
        if abs_h >= 24:
            return f"Hace {abs_h // 24}d {abs_h % 24}h", "badge-danger"
        return f"Hace {abs_h}h", "badge-danger"
    elif hours < 24:
        return f"{int(hours)}h", "badge-warning"
    elif hours < 48:
        return f"1d {int(hours - 24)}h", "badge-success"
    else:
        return f"{int(hours / 24)}d", "badge-success"


def _enrich_order(item: dict) -> dict:
    """Enriquece un pedido con datos procesados."""
    order = item["order"]
    shipment = item.get("shipment")

    deadline_str = _get_deadline(shipment)
    ship_by = _get_ship_by_date(shipment)
    delivery_str = _get_delivery_date(shipment)
    status_label, status_cls, category = _classify_status(shipment, deadline_str)
    tiempo_text, tiempo_cls = _tiempo_restante(deadline_str)

    return {
        "order_id": order.get("id", "?"),
        "shipment_id": item.get("shipment_id"),
        "buyer": order.get("buyer", {}).get("nickname", "—"),
        "total": order.get("total_amount", 0),
        "currency": order.get("currency_id", "MXN"),
        "date_created": order.get("date_created", ""),
        "deadline_str": deadline_str,
        "ship_by": ship_by,
        "delivery_str": delivery_str,
        "status_label": status_label,
        "status_cls": status_cls,
        "category": category,
        "tiempo_text": tiempo_text,
        "tiempo_cls": tiempo_cls,
        "logistic": shipment.get("logistic_type", "—") if shipment else "—",
        "shipping_status_raw": shipment.get("status") if shipment else None,
        "shipping_substatus_raw": shipment.get("substatus") if shipment else None,
        "items": [
            {
                "title": oi.get("item", {}).get("title", "?"),
                "qty": oi.get("quantity", 1),
                "sku": oi.get("item", {}).get("seller_sku", ""),
                "unit_price": oi.get("unit_price", 0),
                "thumbnail": oi.get("item", {}).get("thumbnail", ""),
            }
            for oi in order.get("order_items", [])
        ],
    }


def _build_product_html(items: list[dict]) -> str:
    html = ""
    for p in items:
        sku = f' <span class="sku">SKU: {p["sku"]}</span>' if p.get("sku") else ""
        html += f'<div class="product-line">{p["title"]} <strong>x{p["qty"]}</strong>{sku}</div>'
    return html


# ── Sort helpers ──

CATEGORY_ORDER = {"delayed": 0, "ready": 1, "pending": 2, "shipped": 3, "other": 4}


def _sort_key(order: dict) -> tuple:
    """Ordena: categoría primero (delayed=0), luego por deadline más cercano."""
    cat = CATEGORY_ORDER.get(order["category"], 99)
    deadline_dt = _parse_date(order["deadline_str"])
    if not deadline_dt:
        deadline_dt = _parse_date(order["date_created"]) or datetime.max.replace(tzinfo=timezone.utc)
    return (cat, deadline_dt)


# ── Page builders ──

def _build_order_card_html(o: dict) -> str:
    """Card de un pedido para desktop y mobile."""
    is_delayed = o["category"] == "delayed"

    # Estilos según estado
    if is_delayed:
        border_color = "var(--danger)"
        bg = "var(--danger-bg)"
        header_bg = "#fecaca"
    elif o["category"] == "ready":
        border_color = "var(--accent)"
        bg = "var(--surface)"
        header_bg = "var(--accent-soft)"
    elif o["category"] == "shipped":
        border_color = "var(--success)"
        bg = "var(--surface)"
        header_bg = "var(--success-bg)"
    else:
        border_color = "var(--warning)"
        bg = "var(--surface)"
        header_bg = "var(--warning-bg)"

    items_html = _build_product_html(o["items"])

    deadline_display = _format_date_short(o["deadline_str"]) if o["deadline_str"] else "Sin fecha"
    delivery_display = _format_date_short(o["delivery_str"]) if o.get("delivery_str") else "—"

    pulse_class = " pulse" if is_delayed else ""

    # Thumbnail principal (primer item con foto)
    main_thumb = next((i.get("thumbnail", "") for i in o["items"] if i.get("thumbnail")), "")
    thumb_html = f'<img src="{main_thumb}" class="pedido-thumb" alt="producto">' if main_thumb else '<div class="pedido-thumb pedido-thumb-empty"></div>'

    label_btn = ""
    if o.get("shipment_id") and o.get("shipping_substatus_raw") in ("ready_to_print", "printed", "handling_time_over"):
        label_btn = f'<a href="https://www.mercadolibre.com.mx/envios/{o["shipment_id"]}/ver_etiqueta" target="_blank" class="btn btn-label">🖨️ Imprimir etiqueta</a>'

    deadline_style = "color:var(--danger);font-weight:700;" if is_delayed else "font-weight:600;"

    return f"""
    <div class="pedido-card" style="border-left:4px solid {border_color};background:{bg};">
        <div class="pedido-header" style="background:{header_bg};">
            <div class="pedido-title">
                <strong>Pedido #{o["order_id"]}</strong>
                <span style="color:var(--text-secondary);font-size:13px;">&middot; {o["buyer"]}</span>
            </div>
            <div class="pedido-badges">
                <span class="badge {o["status_cls"]}{pulse_class}">{o["status_label"]}</span>
                <span class="badge {o["tiempo_cls"]}">{o["tiempo_text"]}</span>
                {label_btn}
            </div>
        </div>

        <div class="pedido-body">
            <div class="pedido-items">
                {items_html}
            </div>
            <div class="pedido-meta">
                <div class="meta-item">
                    <span class="meta-label">Fecha de venta</span>
                    <span class="meta-value">{_format_date_short(o["date_created"])}</span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">Despachar antes de</span>
                    <span class="meta-value" style="{deadline_style}">{deadline_display}</span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">Entrega estimada</span>
                    <span class="meta-value">{delivery_display}</span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">Total</span>
                    <span class="meta-value"><strong>${o["total"]:,.2f} {o["currency"]}</strong></span>
                </div>
            </div>
            <div class="pedido-thumb-wrap">
                {thumb_html}
            </div>
        </div>
    </div>"""


def _build_section(title: str, icon: str, orders: list[dict], section_id: str) -> str:
    if not orders:
        return ""

    is_delayed = section_id == "delayed"
    border_color = {
        "delayed": "var(--danger)",
        "ready": "var(--accent)",
        "shipped": "var(--success)",
        "pending": "var(--warning)",
    }.get(section_id, "var(--border)")

    cards_html = "".join(_build_order_card_html(o) for o in orders)

    return f"""
    <div class="section" style="border-top:3px solid {border_color};">
        <div class="section-header">
            <h2>{icon} {title} <span class="section-count">({len(orders)})</span></h2>
        </div>
        {cards_html}
    </div>"""


# ── Extra CSS for pedido cards ──

VENTAS_CSS = """
<style>
    .section {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: var(--radius);
        box-shadow: var(--shadow);
        overflow: hidden;
        margin-bottom: 24px;
    }
    .section-header {
        padding: 16px 20px;
        border-bottom: 1px solid var(--border);
    }
    .section-header h2 {
        font-size: 16px;
        font-weight: 600;
    }
    .section-count {
        font-weight: 400;
        color: var(--text-muted);
        font-size: 14px;
    }

    .pedido-card {
        border-bottom: 1px solid var(--border);
        transition: background 0.1s ease;
    }
    .pedido-card:last-child {
        border-bottom: none;
    }

    .pedido-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 12px 20px;
        flex-wrap: wrap;
        gap: 8px;
    }
    .pedido-title {
        display: flex;
        align-items: center;
        gap: 8px;
        flex-wrap: wrap;
        font-size: 15px;
    }
    .pedido-badges {
        display: flex;
        gap: 6px;
        flex-wrap: wrap;
    }

    .pedido-body {
        padding: 12px 20px 16px;
        display: grid;
        grid-template-columns: 1fr auto 110px;
        gap: 20px;
        align-items: start;
    }

    .pedido-items {
        font-size: 14px;
    }
    .product-line {
        padding: 3px 0;
    }
    .product-line .sku {
        color: var(--text-muted);
        font-size: 11px;
    }

    .pedido-thumb-wrap {
        display: flex;
        align-items: flex-start;
        justify-content: center;
        padding-top: 2px;
    }
    .pedido-thumb {
        width: 100px;
        height: 100px;
        object-fit: contain;
        border-radius: 10px;
        border: 1px solid var(--border);
        background: #fff;
    }
    .pedido-thumb-empty {
        width: 100px;
        height: 100px;
        border-radius: 10px;
        border: 1px dashed var(--border);
        background: var(--bg);
    }

    .btn-label {
        font-size: 12px;
        padding: 4px 10px;
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: var(--radius);
        color: var(--text);
        text-decoration: none;
        white-space: nowrap;
    }
    .btn-label:hover {
        background: var(--accent-soft);
        border-color: var(--accent);
    }

    .pedido-meta {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 8px 24px;
        font-size: 13px;
        align-content: start;
    }
    .meta-item {
        display: flex;
        flex-direction: column;
    }
    .meta-label {
        color: var(--text-muted);
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.3px;
    }
    .meta-value {
        color: var(--text);
        margin-top: 1px;
    }

    /* Pulse animation for delayed badges */
    .badge.pulse {
        animation: badge-pulse 2s ease-in-out infinite;
    }
    @keyframes badge-pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.6; }
    }

    @media (max-width: 768px) {
        .pedido-header {
            padding: 10px 14px;
            flex-direction: column;
            align-items: flex-start;
        }
        .pedido-body {
            padding: 10px 14px 14px;
            grid-template-columns: 1fr auto;
            gap: 12px;
        }
        .pedido-thumb-wrap {
            grid-column: 2;
            grid-row: 1 / 3;
        }
        .pedido-thumb, .pedido-thumb-empty {
            width: 72px;
            height: 72px;
        }
        .pedido-meta {
            grid-template-columns: 1fr 1fr;
            gap: 10px;
        }
        .section-header {
            padding: 12px 14px;
        }
    }
</style>
"""


# ── Routes ──

@router.get("/", response_class=HTMLResponse)
async def ventas_pendientes():
    """Muestra los pedidos pendientes organizados por prioridad."""
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

    # Enriquecer y filtrar
    orders = []
    for item in data:
        shipment = item.get("shipment")
        if shipment and shipment.get("status") in ("delivered", "cancelled"):
            continue
        orders.append(_enrich_order(item))

    # Ordenar por prioridad y luego deadline
    orders.sort(key=_sort_key)

    # Separar por categoría
    delayed = [o for o in orders if o["category"] == "delayed"]
    ready = [o for o in orders if o["category"] == "ready"]
    pending = [o for o in orders if o["category"] == "pending"]
    shipped = [o for o in orders if o["category"] == "shipped"]

    total_amount = sum(o["total"] for o in orders)

    content = f"""
        {VENTAS_CSS}

        <div style="display:flex;justify-content:space-between;align-items:start;flex-wrap:wrap;gap:8px;">
            <div>
                <h1 class="page-title">Ventas Pendientes</h1>
                <p class="page-subtitle">Pedidos organizados por prioridad de envío</p>
            </div>
            <a href="/ventas/" class="btn" onclick="this.innerHTML='Cargando...';this.style.pointerEvents='none';">Actualizar</a>
        </div>

        <div class="stats">
            <div class="stat-card danger">
                <div class="stat-label">Demorados</div>
                <div class="stat-value">{len(delayed)}</div>
                <div class="stat-detail">Acción inmediata</div>
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
                <div class="stat-detail">MXN en {len(orders)} pedido{"s" if len(orders) != 1 else ""}</div>
            </div>
        </div>

        {_build_section("Demorados", "🔴", delayed, "delayed")}
        {_build_section("Listos para enviar", "📦", ready, "ready")}
        {_build_section("Pendientes", "⏳", pending, "pending")}
        {_build_section("En camino", "🚚", shipped, "shipped")}

        {"" if orders else '<div class="empty-state"><div class="icon">🎉</div><p>No hay ventas pendientes</p></div>'}
    """
    return HTMLResponse(content=base_layout("Ventas Pendientes", content, active="ventas"))


@router.get("/debug")
async def ventas_debug():
    """Muestra el shipment COMPLETO de ML para ver todas las fechas disponibles."""
    try:
        data = await meli.get_pending_shipments()
    except Exception as e:
        return {"error": str(e)}

    results = []
    for item in data:
        shipment = item.get("shipment")
        order = item["order"]

        # Extraer todas las fechas posibles del shipment
        fechas = {}
        if shipment:
            fechas = {
                "shipping_option": shipment.get("shipping_option"),
                "date_created": shipment.get("date_created"),
                "last_updated": shipment.get("last_updated"),
                "date_first_printed": shipment.get("date_first_printed"),
                "estimated_handling_limit": shipment.get("estimated_handling_limit"),
                "estimated_delivery_time": shipment.get("estimated_delivery_time"),
            }

        results.append({
            "order_id": order.get("id"),
            "order_status": order.get("status"),
            "buyer": order.get("buyer", {}).get("nickname"),
            "items_count": len(order.get("order_items", [])),
            "shipping_status": shipment.get("status") if shipment else None,
            "shipping_substatus": shipment.get("substatus") if shipment else None,
            "logistic_type": shipment.get("logistic_type") if shipment else None,
            "fechas_encontradas": fechas,
            "_shipment_keys": list(shipment.keys()) if shipment else [],
        })
    return {"total": len(results), "orders": results}


@router.get("/etiqueta/{shipment_id}")
async def get_etiqueta(shipment_id: str):
    """Descarga la etiqueta de envío en PDF desde ML."""
    pdf = await meli.get_label_pdf(shipment_id)
    if not pdf:
        return JSONResponse({"error": "No se pudo obtener la etiqueta"}, status_code=404)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="etiqueta-{shipment_id}.pdf"'},
    )


@router.get("/api")
async def ventas_api():
    """JSON de ventas pendientes."""
    try:
        data = await meli.get_pending_shipments()
    except Exception as e:
        return {"error": str(e)}

    pending = []
    for item in data:
        shipment = item.get("shipment")
        if shipment and shipment.get("status") in ("delivered", "cancelled"):
            continue
        o = _enrich_order(item)
        pending.append({
            "order_id": o["order_id"],
            "buyer": o["buyer"],
            "items": o["items"],
            "total": o["total"],
            "currency": o["currency"],
            "status": o["status_label"],
            "category": o["category"],
            "deadline": o["deadline_str"],
            "delivery_date": o["delivery_str"],
            "logistic_type": o["logistic"],
            "date_created": o["date_created"],
        })

    return {"total_pending": len(pending), "orders": pending}
