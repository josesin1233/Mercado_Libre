import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from app.order_manager import order_manager


async def load_orders_from_ml() -> int:
    """Carga órdenes recientes pagadas desde ML al arrancar, para no perder estado tras un reinicio."""
    from app.meli_client import meli
    from app.models import Order, OrderItem, ShippingPriority
    from app.routes.webhooks import classify_shipping_priority

    try:
        enriched = await meli.get_pending_shipments()
        count = 0
        for entry in enriched:
            order_data = entry["order"]
            shipment = entry["shipment"]

            if order_data.get("status") != "paid":
                continue

            priority = ShippingPriority.NORMAL
            deadline = None
            if shipment:
                priority = classify_shipping_priority(shipment)
                dl = shipment.get("shipping_option", {}).get("estimated_handling_limit", {}).get("date")
                if dl:
                    deadline = datetime.fromisoformat(dl.replace("Z", "+00:00"))

            items = [
                OrderItem(
                    item_id=item["item"]["id"],
                    title=item["item"]["title"],
                    quantity=item["quantity"],
                    sku=item["item"].get("seller_sku"),
                )
                for item in order_data.get("order_items", [])
            ]

            order = Order(
                order_id=int(order_data["id"]),
                buyer_nickname=order_data.get("buyer", {}).get("nickname", ""),
                items=items,
                shipping_id=entry["shipment_id"],
                shipping_priority=priority,
                shipping_deadline=deadline,
                status="paid",
                date_created=order_data.get("date_created", datetime.now(timezone.utc).isoformat()),
                total_amount=order_data.get("total_amount", 0),
            )
            await order_manager.add_order(order)
            count += 1

        return count
    except Exception as exc:
        print(f"[Startup] Error al cargar órdenes desde ML: {exc}")
        return 0


async def auto_cleanup_loop():
    """Cada 30 minutos limpia órdenes completadas automáticamente."""
    while True:
        try:
            removed = await order_manager.cleanup_completed()
            if removed:
                print(f"[Auto-cleanup] Se eliminaron {len(removed)} órdenes completadas: {removed}")
        except Exception as exc:
            print(f"[Auto-cleanup] Error durante cleanup: {exc}")
        await asyncio.sleep(1800)  # 30 minutos


@asynccontextmanager
async def lifespan(app):
    """Inicia tareas en segundo plano al arrancar la app."""
    # Inicializar base de datos (crea tablas si no existen)
    try:
        from app.database import init_db
        await init_db()
        print("[Startup] Base de datos inicializada")
    except Exception as exc:
        print(f"[Startup] DB no disponible (sin DATABASE_URL o error de conexión): {exc}")

    # Cargar tokens persistidos en BD (sobrescriben env vars si existen)
    try:
        from app.token_store import load_tokens
        from app.config import settings
        from app.meli_client import meli
        tokens = await load_tokens()
        if tokens:
            settings.ACCESS_TOKEN = tokens["access_token"]
            settings.REFRESH_TOKEN = tokens["refresh_token"]
            meli.token = tokens["access_token"]
            print("[Startup] Tokens cargados desde BD")
    except Exception as exc:
        print(f"[Startup] No se pudieron cargar tokens desde BD: {exc}")

    # Cargar órdenes pagadas desde ML para restaurar estado tras reinicio
    try:
        count = await load_orders_from_ml()
        print(f"[Startup] {count} órdenes cargadas desde ML")
    except Exception as exc:
        print(f"[Startup] No se pudieron cargar órdenes: {exc}")

    # Registrar webhook de Telegram si hay PUBLIC_URL configurada
    try:
        from app.config import settings
        import httpx
        if settings.TELEGRAM_BOT_TOKEN and settings.PUBLIC_URL:
            webhook_url = f"{settings.PUBLIC_URL.rstrip('/')}/telegram/updates"
            async with httpx.AsyncClient() as client:
                r = await client.post(
                    f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/setWebhook",
                    json={"url": webhook_url},
                )
            result = r.json()
            if result.get("ok"):
                print(f"[Startup] Webhook de Telegram registrado: {webhook_url}")
            else:
                print(f"[Startup] Error al registrar webhook de Telegram: {result}")
    except Exception as exc:
        print(f"[Startup] No se pudo registrar webhook de Telegram: {exc}")

    task = asyncio.create_task(auto_cleanup_loop())
    print("[Startup] Auto-cleanup de órdenes iniciado")
    yield
    task.cancel()
    print("[Shutdown] Auto-cleanup detenido")
