from fastapi import APIRouter
from fastapi.responses import RedirectResponse
from app.config import settings
from app.meli_client import meli
import httpx

router = APIRouter()


@router.get("/login")
def login():
    """Redirige al usuario a Mercado Libre para autorizar la app."""
    auth_url = (
        f"https://auth.mercadolibre.com.mx/authorization"
        f"?response_type=code"
        f"&client_id={settings.APP_ID}"
        f"&redirect_uri={settings.REDIRECT_URI}"
    )
    return RedirectResponse(url=auth_url)


@router.get("/callback")
async def callback(code: str):
    """Recibe el código de autorización y lo intercambia por tokens."""
    async with httpx.AsyncClient() as client:
        r = await client.post(
            "https://api.mercadolibre.com/oauth/token",
            data={
                "grant_type": "authorization_code",
                "client_id": settings.APP_ID,
                "client_secret": settings.CLIENT_SECRET,
                "code": code,
                "redirect_uri": settings.REDIRECT_URI,
            },
        )

    if r.status_code != 200:
        return {
            "status": "error",
            "ml_status_code": r.status_code,
            "ml_response": r.json(),
            "debug": {
                "app_id_set": bool(settings.APP_ID),
                "secret_set": bool(settings.CLIENT_SECRET),
                "redirect_uri": settings.REDIRECT_URI,
                "code_received": code,
            },
        }

    tokens = r.json()

    # Guardar tokens en memoria
    settings.ACCESS_TOKEN = tokens["access_token"]
    settings.REFRESH_TOKEN = tokens["refresh_token"]
    meli.token = tokens["access_token"]

    return {
        "status": "authenticated",
        "message": "Tokens obtenidos. Guárdalos en tus variables de entorno.",
        "access_token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"],
        "expires_in": tokens.get("expires_in"),
    }
