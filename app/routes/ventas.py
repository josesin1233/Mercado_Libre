from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from datetime import datetime, timezone
from app.meli_client import meli

router = APIRouter()


def _tiempo_restante(deadline_str: str | None) -> str:
    if not deadline_str:
        return "Sin fecha límite"
    try:
        deadline = datetime.fromisoformat(deadline_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        diff = deadline - now
        hours = diff.total_seconds() / 3600
        if hours < 0:
            return "⚠️ VENCIDO"
        elif hours < 24:
            return f"🔴 {int(hours)}h restantes"
        elif hours < 48:
            return f"🟡 {int(hours)}h restantes"
        else:
            return f"🟢 {int(hours / 24)}d restantes"
    except Exception:
        return "—"


def _status_envio(shipment: dict | None) -> str:
    if not shipment:
        return "Sin info"
    status = shipment.get("status", "")
    substatus = shipment.get("substatus", "")
    mapping = {
        "pending": "📦 Pendiente",
        "ready_to_ship": "📦 Listo para enviar",
        "shipped": "🚚 En camino",
        "delivered": "✅ Entregado",
        "not_delivered": "❌ No entregado",
        "cancelled": "🚫 Cancelado",
    }
    label = mapping.get(status, status)
    if substatus:
        label += f" ({substatus})"
    return label


@router.get("/", response_class=HTMLResponse)
async def ventas_pendientes():
    """Muestra las ventas pendientes de entregar en una página web."""
    try:
        data = await meli.get_pending_shipments()
    except Exception as e:
        return HTMLResponse(
            content=f"""<html><body style="font-family:sans-serif;padding:40px;">
            <h1>Error al obtener ventas</h1>
            <p style="color:red;">{e}</p>
            <p>Verifica que ACCESS_TOKEN y USER_ID estén configurados correctamente.</p>
            </body></html>""",
            status_code=500,
        )

    # Filtrar solo las que NO están entregadas ni canceladas
    pending = []
    for item in data:
        shipment = item.get("shipment")
        if shipment and shipment.get("status") in ("delivered", "cancelled"):
            continue
        pending.append(item)

    rows = ""
    for i, item in enumerate(pending, 1):
        order = item["order"]
        shipment = item.get("shipment")

        # Info de productos
        productos = ""
        for oi in order.get("order_items", []):
            title = oi.get("item", {}).get("title", "?")
            qty = oi.get("quantity", 1)
            sku = oi.get("item", {}).get("seller_sku", "")
            sku_text = f' <span style="color:#888;">SKU: {sku}</span>' if sku else ""
            productos += f"<div>• {title} <strong>x{qty}</strong>{sku_text}</div>"

        # Info del comprador
        buyer = order.get("buyer", {}).get("nickname", "—")

        # Monto
        total = order.get("total_amount", 0)
        currency = order.get("currency_id", "MXN")

        # Fecha de venta
        created = order.get("date_created", "")
        try:
            dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
            fecha = dt.strftime("%d/%m/%Y %H:%M")
        except Exception:
            fecha = created

        # Info de envío
        status_envio = _status_envio(shipment)
        deadline = None
        if shipment:
            deadline = (
                shipment.get("shipping_option", {})
                .get("estimated_handling_limit", {})
                .get("date")
            )
        tiempo = _tiempo_restante(deadline)

        # Logistic type
        logistic = shipment.get("logistic_type", "—") if shipment else "—"

        order_id = order.get("id", "?")

        rows += f"""
        <tr>
            <td>{i}</td>
            <td><strong>#{order_id}</strong><br><small>{fecha}</small></td>
            <td>{buyer}</td>
            <td>{productos}</td>
            <td>${total:,.2f} {currency}</td>
            <td>{status_envio}</td>
            <td>{logistic}</td>
            <td>{tiempo}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ventas Pendientes - Mercado Libre</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; color: #333; }}
        .header {{ background: #FFE600; padding: 20px 40px; display: flex; align-items: center; justify-content: space-between; }}
        .header h1 {{ font-size: 24px; color: #333; }}
        .header .badge {{ background: #333; color: #FFE600; padding: 6px 16px; border-radius: 20px; font-weight: bold; font-size: 18px; }}
        .container {{ max-width: 1200px; margin: 30px auto; padding: 0 20px; }}
        .summary {{ display: flex; gap: 20px; margin-bottom: 30px; }}
        .card {{ background: white; border-radius: 12px; padding: 20px; flex: 1; box-shadow: 0 2px 8px rgba(0,0,0,0.08); text-align: center; }}
        .card .number {{ font-size: 36px; font-weight: bold; }}
        .card .label {{ color: #666; margin-top: 4px; }}
        table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }}
        th {{ background: #2D3277; color: white; padding: 14px 12px; text-align: left; font-size: 13px; text-transform: uppercase; }}
        td {{ padding: 12px; border-bottom: 1px solid #eee; font-size: 14px; vertical-align: top; }}
        tr:hover {{ background: #FFFDE7; }}
        .empty {{ text-align: center; padding: 60px; color: #999; font-size: 18px; }}
        .refresh {{ background: #2D3277; color: white; border: none; padding: 10px 24px; border-radius: 8px; cursor: pointer; font-size: 14px; text-decoration: none; }}
        .refresh:hover {{ background: #3D42A7; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Ventas Pendientes</h1>
        <div>
            <span class="badge">{len(pending)} pendiente{"s" if len(pending) != 1 else ""}</span>
            <a href="/ventas/" class="refresh" style="margin-left:12px;">Actualizar</a>
        </div>
    </div>
    <div class="container">
        <div class="summary">
            <div class="card">
                <div class="number">{len(pending)}</div>
                <div class="label">Pendientes</div>
            </div>
            <div class="card">
                <div class="number">{len([p for p in pending if p.get("shipment") and p["shipment"].get("status") == "ready_to_ship"])}</div>
                <div class="label">Listas para enviar</div>
            </div>
            <div class="card">
                <div class="number">{sum(order.get("total_amount", 0) for item in pending for order in [item["order"]]):,.0f}</div>
                <div class="label">MXN total</div>
            </div>
        </div>
        {"<table><thead><tr><th>#</th><th>Orden</th><th>Comprador</th><th>Productos</th><th>Monto</th><th>Envío</th><th>Tipo</th><th>Tiempo</th></tr></thead><tbody>" + rows + "</tbody></table>" if pending else '<div class="empty">🎉 No hay ventas pendientes de entregar</div>'}
    </div>
</body>
</html>"""
    return HTMLResponse(content=html)


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
