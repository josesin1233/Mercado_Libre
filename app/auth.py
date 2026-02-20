from fastapi import APIRouter
from fastapi.responses import RedirectResponse
from app.config import settings
from app.meli_client import meli
import httpx
import traceback
import secrets
import hashlib
import base64

router = APIRouter()


def _generate_pkce():
    code_verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(code_verifier.encode()).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return code_verifier, code_challenge


@router.get("/login")
def login():
    """Redirige al usuario a Mercado Libre para autorizar la app."""
    code_verifier, code_challenge = _generate_pkce()

    auth_url = (
        f"https://auth.mercadolibre.com.mx/authorization"
        f"?response_type=code"
        f"&client_id={settings.APP_ID}"
        f"&redirect_uri={settings.REDIRECT_URI}"
        f"&scope=offline_access+read+write"
        f"&code_challenge={code_challenge}"
        f"&code_challenge_method=S256"
        f"&state={code_verifier}"
    )
    return RedirectResponse(url=auth_url)


@router.get("/callback")
async def callback(code: str, state: str = ""):
    """Recibe el código de autorización y lo intercambia por tokens."""
    try:
        payload = {
            "grant_type": "authorization_code",
            "client_id": settings.APP_ID,
            "client_secret": settings.CLIENT_SECRET,
            "code": code,
            "redirect_uri": settings.REDIRECT_URI,
            "code_verifier": state,
        }

        async with httpx.AsyncClient() as client:
            r = await client.post(
                "https://api.mercadolibre.com/oauth/token",
                data=payload,
            )

        response_data = r.json()

        if r.status_code != 200:
            return {
                "status": "error",
                "ml_status_code": r.status_code,
                "ml_response": response_data,
                "debug": {
                    "app_id_set": bool(settings.APP_ID),
                    "secret_set": bool(settings.CLIENT_SECRET),
                    "redirect_uri": settings.REDIRECT_URI,
                    "code_received": code,
                },
            }

        # Guardar tokens en memoria
        settings.ACCESS_TOKEN = response_data["access_token"]
        if "refresh_token" in response_data:
            settings.REFRESH_TOKEN = response_data["refresh_token"]
        meli.token = response_data["access_token"]

        return {
            "status": "authenticated",
            "message": "Tokens obtenidos. Guárdalos en tus variables de entorno.",
            "access_token": response_data["access_token"],
            "refresh_token": response_data.get("refresh_token", "no incluido - necesitas scope offline_access"),
            "expires_in": response_data.get("expires_in"),
            "full_response": response_data,
        }

    except Exception as e:
        return {
            "status": "crash",
            "error": str(e),
            "traceback": traceback.format_exc(),
        }
