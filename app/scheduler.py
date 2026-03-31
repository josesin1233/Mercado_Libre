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

    task = asyncio.create_task(auto_cleanup_loop())
    print("[Startup] Auto-cleanup de órdenes iniciado")
    yield
    task.cancel()
    print("[Shutdown] Auto-cleanup detenido")
