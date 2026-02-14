import asyncio
from contextlib import asynccontextmanager
from app.order_manager import order_manager


async def auto_cleanup_loop():
    """Cada 30 minutos limpia órdenes completadas automáticamente."""
    while True:
        removed = order_manager.cleanup_completed()
        if removed:
            print(f"[Auto-cleanup] Se eliminaron {len(removed)} órdenes completadas: {removed}")
        await asyncio.sleep(1800)  # 30 minutos


@asynccontextmanager
async def lifespan(app):
    """Inicia tareas en segundo plano al arrancar la app."""
    task = asyncio.create_task(auto_cleanup_loop())
    print("[Startup] Auto-cleanup de órdenes iniciado")
    yield
    task.cancel()
    print("[Shutdown] Auto-cleanup detenido")
