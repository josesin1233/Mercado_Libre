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

    # URL de tu otra página que recibe las notificaciones de ML
    EXTERNAL_WEBHOOK_SOURCE: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
