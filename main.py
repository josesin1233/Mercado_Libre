from fastapi import FastAPI
from app.routes import orders, webhooks, notifications
from app.auth import router as auth_router
from app.scheduler import lifespan

app = FastAPI(title="Mercado Libre - Gestión de Ventas", lifespan=lifespan)

app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(orders.router, prefix="/orders", tags=["Órdenes"])
app.include_router(webhooks.router, prefix="/webhooks", tags=["Webhooks"])
app.include_router(notifications.router, prefix="/notifications", tags=["Notificaciones"])


@app.get("/")
def root():
    return {"status": "ok", "app": "Mercado Libre - Gestión de Ventas"}


@app.get("/health")
def health():
    from app.order_manager import order_manager
    return {
        "status": "healthy",
        "pending_orders": order_manager.get_pending_count(),
        "urgent_orders": len(order_manager.get_urgent_orders()),
    }
