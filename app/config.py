from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_ID: str = ""
    CLIENT_SECRET: str = ""
    REDIRECT_URI: str = ""
    ACCESS_TOKEN: str = ""
    REFRESH_TOKEN: str = ""
    USER_ID: str = ""

    # IPs permitidas (separadas por coma). Si está vacío, permite todo.
    ALLOWED_IPS: str = ""

    # URL pública del servidor (ej: https://xxx.railway.app) — para registrar webhook de Telegram
    PUBLIC_URL: str = ""

    # URL de tu otra página que recibe las notificaciones de ML
    EXTERNAL_WEBHOOK_SOURCE: str = ""

    # Notificaciones — Telegram
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""  # chat_id al que llegan todas las notis (privado, grupo o canal)

    # Notificaciones — ntfy.sh
    NTFY_TOPIC: str = ""  # ej: "ml-josesolis-ventas" (debe ser único)

    # PostgreSQL — formato: postgresql+asyncpg://user:pass@host:port/db
    DATABASE_URL: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
