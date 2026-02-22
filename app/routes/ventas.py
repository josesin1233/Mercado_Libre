from fastapi import APIRouter
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from datetime import datetime, timezone
from app.meli_client import meli
from app.ui import base_layout

router = APIRouter()


# ── Date helpers ─────────────────────────────────────────────────────────────

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


# ── Shipment date extractors ──────────────────────────────────────────────────

def _get_deadline(shipment: dict | None) -> str | None:
    """Busca la fecha límite de despacho probando varias rutas del API de ML."""
    if not shipment:
        return None
    so = shipment.get("shipping_option") or {}
    # Ruta 1: estimated_delivery_limit
    d1 = (so.get("estimated_delivery_limit") or {}).get("date")
    # Ruta 2: buffering.date (pedidos express priority_class 60 — el carrier
    # espera el paquete en esa fecha, que puede ser anterior al delivery limit)
    d2 = (so.get("buffering") or {}).get("date")
    if d1 and d2:
        try:
            dt1 = datetime.fromisoformat(d1.replace("Z", "+00:00"))
            dt2 = datetime.fromisoformat(d2.replace("Z", "+00:00"))
            return d1 if dt1 <= dt2 else d2
        except Exception:
            pass
    if d1:
        return d1
    if d2:
        return d2
    # Ruta 3: estimated_handling_limit dentro de shipping_option
    d = (so.get("estimated_handling_limit") or {}).get("date")
    if d:
        return d
    # Ruta 4: estimated_handling_limit directo en el shipment
    ehl = shipment.get("estimated_handling_limit")
    if isinstance(ehl, dict):
        d = ehl.get("date")
        if d:
            return d
    elif isinstance(ehl, str):
        return ehl
    # Ruta 5: estimated_delivery_final como último recurso
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
    """Obtiene la mejor fecha disponible para 'cuándo debería enviarse'."""
    deadline = _get_deadline(shipment)
    if deadline:
        return deadline
    delivery = _get_delivery_date(shipment)
    if delivery:
        return delivery
    if not shipment:
        return None
    return shipment.get("date_created")


# ── Status classification ─────────────────────────────────────────────────────

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
                "ready_to_print": "DEMORADO — Imprimir",
                "printed": "DEMORADO — Despachar",
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

    label = status + (f" ({substatus})" if substatus else "")
    return label, "badge-neutral", "pending"


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
        return f"{int(hours)}h restantes", "badge-warning"
    elif hours < 48:
        return f"1d {int(hours - 24)}h", "badge-success"
    else:
        return f"{int(hours / 24)}d restantes", "badge-success"


# ── Data enrichment ───────────────────────────────────────────────────────────

def _extract_album(order_item: dict) -> str:
    """Extrae el nombre del álbum desde variation_attributes del order_item."""
    attrs = order_item.get("item", {}).get("variation_attributes") or []
    for attr in attrs:
        name = (attr.get("name") or "").lower()
        if "lbum" in name or "versi" in name:
            return attr.get("value_name") or ""
    return ""


def _enrich_order(item: dict) -> dict:
    """Enriquece un pedido con datos procesados para UI y API."""
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
        "buyer_id": order.get("buyer", {}).get("id"),
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
                "album": _extract_album(oi),
                "qty": oi.get("quantity", 1),
                "sku": oi.get("item", {}).get("seller_sku", "") or "",
                "unit_price": oi.get("unit_price", 0),
                "thumbnail": oi.get("item", {}).get("thumbnail", "") or "",
                "item_id": str(oi.get("item", {}).get("id", "")),
            }
            for oi in order.get("order_items", [])
        ],
    }


# ── HTML builders ─────────────────────────────────────────────────────────────

def _build_product_html(items: list[dict]) -> str:
    html = ""
    for p in items:
        sku_html = (
            f'<div class="item-row-sku">SKU: {p["sku"]}</div>'
            if p.get("sku") else ""
        )
        album_html = (
            f'<div class="item-row-album">{p["album"]}</div>'
            if p.get("album") else ""
        )
        thumb_html = (
            f'<img src="{p["thumbnail"]}" class="item-row-thumb" alt="">'
            if p.get("thumbnail")
            else '<div class="item-row-thumb-empty"></div>'
        )
        html += f"""
        <div class="item-row">
            {thumb_html}
            <div class="item-row-info">
                <div class="item-row-title">{p["title"]}</div>
                {album_html}
                {sku_html}
            </div>
            <span class="qty">x{p["qty"]}</span>
        </div>"""
    return html


def _build_order_card_html(o: dict) -> str:
    """Card de un pedido — clickable para abrir el modal de detalle."""
    is_delayed = o["category"] == "delayed"

    border_color_map = {
        "delayed": "var(--danger)",
        "ready":   "var(--accent)",
        "shipped": "var(--success)",
        "pending": "var(--warning)",
    }
    header_bg_map = {
        "delayed": "#fef2f2",
        "ready":   "var(--accent-soft)",
        "shipped": "var(--success-bg)",
        "pending": "var(--warning-bg)",
    }

    border_color = border_color_map.get(o["category"], "var(--border-strong)")
    header_bg = header_bg_map.get(o["category"], "var(--surface-2)")

    items_html = _build_product_html(o["items"])
    deadline_display = _format_date_short(o["deadline_str"]) if o["deadline_str"] else "Sin fecha"
    delivery_display = _format_date_short(o["delivery_str"]) if o.get("delivery_str") else "—"
    pulse_class = " pulse" if is_delayed else ""
    deadline_style = "color:var(--danger);font-weight:700;" if is_delayed else ""

    # Label button
    label_btn = ""
    ok_sub = ("ready_to_print", "printed", "handling_time_over")
    if o.get("shipment_id") and o.get("shipping_substatus_raw") in ok_sub:
        label_btn = (
            f'<a href="https://www.mercadolibre.com.mx/ventas/{o["order_id"]}/detalle"'
            f' target="_blank" class="btn-label" onclick="event.stopPropagation()">'
            f'Imprimir etiqueta</a>'
        )

    order_id = o["order_id"]
    shipment_id = o.get("shipment_id") or order_id

    return f"""
    <div class="pedido-card" style="border-left:4px solid {border_color};"
         onclick="openShipmentModal({shipment_id!r})" role="button" tabindex="0"
         onkeydown="if(event.key==='Enter')openShipmentModal({shipment_id!r})">
        <div class="pedido-header" style="background:{header_bg};">
            <div class="pedido-title">
                <strong>#{order_id}</strong>
                <span class="buyer">{o["buyer"]}</span>
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
        </div>
    </div>"""


def _build_section(title: str, icon: str, orders: list[dict], section_id: str) -> str:
    if not orders:
        return ""

    border_map = {
        "delayed": "var(--danger)",
        "ready":   "var(--accent)",
        "shipped": "var(--success)",
        "pending": "var(--warning)",
    }
    border_color = border_map.get(section_id, "var(--border)")
    cards_html = "".join(_build_order_card_html(o) for o in orders)

    return f"""
    <div class="section" style="border-top:3px solid {border_color};">
        <div class="section-header">
            <h2>{title} <span class="section-count">({len(orders)})</span></h2>
        </div>
        {cards_html}
    </div>"""


# ── Sort helpers ──────────────────────────────────────────────────────────────

CATEGORY_ORDER = {"delayed": 0, "ready": 1, "pending": 2, "shipped": 3, "other": 4}


def _sort_key(order: dict) -> tuple:
    cat = CATEGORY_ORDER.get(order["category"], 99)
    deadline_dt = _parse_date(order["deadline_str"])
    if not deadline_dt:
        deadline_dt = _parse_date(order["date_created"]) or datetime.max.replace(tzinfo=timezone.utc)
    return (cat, deadline_dt)


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
async def ventas_pendientes():
    """Muestra los pedidos pendientes organizados por prioridad."""
    try:
        data = await meli.get_pending_shipments()
    except Exception as e:
        error_content = f"""
            <div class="page-header">
                <div>
                    <h1 class="page-title">Ventas Pendientes</h1>
                    <p class="page-subtitle">Pedidos organizados por prioridad de envío</p>
                </div>
            </div>
            <div class="error-banner">
                <div>
                    <strong>Error al conectar con Mercado Libre</strong>
                    <p>{e}</p>
                    <p style="margin-top:6px;font-size:12px;">Verifica que ACCESS_TOKEN y USER_ID estén configurados.</p>
                </div>
            </div>"""
        return HTMLResponse(content=base_layout("Error — Ventas", error_content, active="ventas"), status_code=500)

    # Enriquecer y filtrar entregados/cancelados
    raw_orders = []
    for item in data:
        order = item["order"]
        if order.get("status") in ("cancelled",):
            continue
        shipment = item.get("shipment")
        if shipment and shipment.get("status") in ("delivered", "cancelled"):
            continue
        raw_orders.append(_enrich_order(item))

    # Agrupar por shipment_id (ML crea un order_id por artículo pero un solo envío)
    CAT_PRIORITY = {"delayed": 0, "ready": 1, "pending": 2, "shipped": 3, "other": 4}
    seen_shipments: dict = {}
    orders = []
    for o in raw_orders:
        sid = o.get("shipment_id")
        if sid and sid in seen_shipments:
            # Combinar items y total en el primer representante del grupo
            existing = seen_shipments[sid]
            existing["items"].extend(o["items"])
            existing["total"] += o["total"]
            # Mantener la categoría más urgente
            if CAT_PRIORITY.get(o["category"], 99) < CAT_PRIORITY.get(existing["category"], 99):
                existing["category"] = o["category"]
                existing["status_label"] = o["status_label"]
                existing["status_cls"] = o["status_cls"]
                existing["tiempo_text"] = o["tiempo_text"]
                existing["tiempo_cls"] = o["tiempo_cls"]
        else:
            if sid:
                seen_shipments[sid] = o
            orders.append(o)

    orders.sort(key=_sort_key)

    delayed = [o for o in orders if o["category"] == "delayed"]
    ready   = [o for o in orders if o["category"] == "ready"]
    pending = [o for o in orders if o["category"] == "pending"]
    shipped = [o for o in orders if o["category"] == "shipped"]

    total_amount = sum(o["total"] for o in orders)
    n = len(orders)

    content = f"""
        <div class="page-header">
            <div>
                <h1 class="page-title">Ventas Pendientes</h1>
                <p class="page-subtitle">Pedidos organizados por prioridad de envío — haz clic en un pedido para ver el detalle</p>
            </div>
            <a href="/ventas/" class="btn" onclick="this.textContent='Cargando…';this.style.pointerEvents='none';">Actualizar</a>
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
                <div class="stat-detail">MXN · {n} pedido{"s" if n != 1 else ""}</div>
            </div>
        </div>

        {_build_section("Demorados", "", delayed, "delayed")}
        {_build_section("Listos para enviar", "", ready, "ready")}
        {_build_section("Pendientes", "", pending, "pending")}
        {_build_section("En camino", "", shipped, "shipped")}

        {"" if orders else '<div class="empty-state"><p>No hay ventas pendientes</p></div>'}
    """
    return HTMLResponse(content=base_layout("Ventas Pendientes", content, active="ventas"))


@router.get("/api/orden/{order_id}")
async def ventas_orden_api(order_id: str):
    """JSON de detalle de una orden específica — consumido por el modal."""
    if not order_id.isdigit():
        return JSONResponse({"error": "order_id inválido"}, status_code=400)
    try:
        data = await meli.get_pending_shipments()
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

    # Buscar la orden en los datos
    for item in data:
        oid = str(item["order"].get("id", ""))
        if oid == order_id:
            enriched = _enrich_order(item)
            return JSONResponse(enriched)

    # No estaba en cache; intentar fetch directo
    try:
        order_data = await meli.get_order(order_id)
        shipping_id = order_data.get("shipping", {}).get("id")
        shipment_data = None
        if shipping_id:
            try:
                shipment_data = await meli.get_shipment(str(shipping_id))
            except Exception:
                pass

        # Fetch thumbnails para los items
        item_ids = [
            str(oi.get("item", {}).get("id", ""))
            for oi in order_data.get("order_items", [])
            if oi.get("item", {}).get("id")
        ]
        thumbnails = await meli.get_items_thumbnails(item_ids) if item_ids else {}
        for oi in order_data.get("order_items", []):
            item_obj = oi.get("item")
            if isinstance(item_obj, dict):
                item_obj["thumbnail"] = thumbnails.get(str(item_obj.get("id", "")), "")

        synthetic = {
            "order": order_data,
            "shipment": shipment_data,
            "shipment_id": shipping_id,
        }
        enriched = _enrich_order(synthetic)
        return JSONResponse(enriched)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=404)


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


@router.get("/api/envio/{shipment_id}")
async def ventas_envio_api(shipment_id: str):
    """
    JSON de detalle de un envío agrupado por shipment_id — consumido por el modal.
    Agrega todas las órdenes que comparten el mismo shipment_id para mostrar
    items y total correctos en pedidos con múltiples cuadros.
    """
    if not shipment_id.isdigit():
        return JSONResponse({"error": "shipment_id inválido"}, status_code=400)
    try:
        data = await meli.get_pending_shipments()
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

    # Juntar todas las órdenes que pertenecen a este shipment
    matching = [
        item for item in data
        if str(item.get("shipment_id", "")) == shipment_id
    ]

    if not matching:
        # Fallback: fetch directo del shipment y su primera orden
        try:
            shipment_data = await meli.get_shipment(shipment_id)
            # Buscar órdenes asociadas al shipment
            order_ids = []
            for item in data:
                if str(item.get("shipment_id", "")) == shipment_id:
                    order_ids.append(str(item["order"].get("id", "")))
            if not order_ids:
                return JSONResponse({"error": "Envío no encontrado"}, status_code=404)
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=404)

    if len(matching) == 1:
        enriched = _enrich_order(matching[0])
        return JSONResponse(enriched)

    # Combinar múltiples órdenes del mismo envío
    CAT_PRIORITY = {"delayed": 0, "ready": 1, "pending": 2, "shipped": 3, "other": 4}
    base = _enrich_order(matching[0])
    for item in matching[1:]:
        extra = _enrich_order(item)
        base["items"].extend(extra["items"])
        base["total"] += extra["total"]
        if CAT_PRIORITY.get(extra["category"], 99) < CAT_PRIORITY.get(base["category"], 99):
            base["category"] = extra["category"]
            base["status_label"] = extra["status_label"]
            base["status_cls"] = extra["status_cls"]
            base["tiempo_text"] = extra["tiempo_text"]
            base["tiempo_cls"] = extra["tiempo_cls"]
    return JSONResponse(base)


@router.get("/etiqueta/{shipment_id}")
async def get_etiqueta(shipment_id: str):
    """Redirige a la página de etiqueta de ML (la API de labels requiere app de integrador)."""
    if not shipment_id.isdigit():
        return JSONResponse({"error": "shipment_id inválido"}, status_code=400)
    return RedirectResponse(
        url=f"https://www.mercadolibre.com.mx/envios/{shipment_id}/ver_etiqueta",
        status_code=302,
    )


@router.get("/api")
async def ventas_api():
    """JSON de todas las ventas pendientes."""
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
