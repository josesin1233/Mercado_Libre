from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse
from app.routes import orders, webhooks, notifications, ventas
from app.routes.dashboard import router as dashboard_router
from app.routes.notificaciones_page import router as notificaciones_page_router
from app.auth import router as auth_router
from app.scheduler import lifespan
from app.config import settings

app = FastAPI(title="Mercado Libre - Gestión de Ventas", lifespan=lifespan)


OPEN_PATHS = {"/", "/health", "/auth/login", "/auth/callback", "/webhooks/receive", "/webhooks/forward"}


@app.middleware("http")
async def ip_whitelist(request: Request, call_next):
    # Dejar pasar rutas que necesitan acceso abierto (healthcheck, webhooks, auth)
    if request.url.path in OPEN_PATHS:
        return await call_next(request)

    if not settings.ALLOWED_IPS:
        return await call_next(request)

    allowed = {ip.strip() for ip in settings.ALLOWED_IPS.split(",") if ip.strip()}
    client_ip = request.client.host

    # Revisar también X-Forwarded-For (Railway usa proxy)
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()

    if client_ip not in allowed:
        return JSONResponse(status_code=403, content={"detail": "IP no autorizada"})

    return await call_next(request)

app.include_router(dashboard_router, tags=["Dashboard"])
app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(orders.router, prefix="/orders", tags=["Órdenes"])
app.include_router(webhooks.router, prefix="/webhooks", tags=["Webhooks"])
app.include_router(notifications.router, prefix="/notifications", tags=["Notificaciones"])
app.include_router(ventas.router, prefix="/ventas", tags=["Ventas"])
app.include_router(notificaciones_page_router, prefix="/notificaciones", tags=["Notificaciones Page"])


@app.get("/health")
def health():
    from app.order_manager import order_manager
    return {
        "status": "healthy",
        "pending_orders": order_manager.get_pending_count(),
        "urgent_orders": len(order_manager.get_urgent_orders()),
    }
