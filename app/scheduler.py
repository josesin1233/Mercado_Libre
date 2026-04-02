import asyncio
from contextlib import asynccontextmanager
from app.order_manager import order_manager


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
