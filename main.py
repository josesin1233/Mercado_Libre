from fastapi import FastAPI
from app.routes import orders, webhooks, notifications
from app.auth import router as auth_router
from app.config import settings

app = FastAPI(title="Mercado Libre - Gestión de Ventas")

app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(orders.router, prefix="/orders", tags=["Órdenes"])
app.include_router(webhooks.router, prefix="/webhooks", tags=["Webhooks"])
app.include_router(notifications.router, prefix="/notifications", tags=["Notificaciones"])


@app.get("/")
def root():
    return {"status": "ok", "app": "Mercado Libre - Gestión de Ventas"}
