"""Persistencia de tokens de ML en PostgreSQL."""

from sqlalchemy import select
from app.database import MeliTokens, get_session_factory


async def load_tokens() -> dict | None:
    """Carga tokens desde la BD. Retorna dict con access_token y refresh_token, o None."""
    try:
        async with get_session_factory()() as session:
            result = await session.execute(select(MeliTokens).where(MeliTokens.id == 1))
            row = result.scalar_one_or_none()
            if row:
                return {"access_token": row.access_token, "refresh_token": row.refresh_token}
    except Exception as exc:
        print(f"[TokenStore] Error al cargar tokens: {exc}")
    return None


async def save_tokens(access_token: str, refresh_token: str) -> None:
    """Guarda (o actualiza) los tokens en la BD."""
    try:
        async with get_session_factory()() as session:
            result = await session.execute(select(MeliTokens).where(MeliTokens.id == 1))
            row = result.scalar_one_or_none()
            if row:
                row.access_token = access_token
                row.refresh_token = refresh_token
            else:
                session.add(MeliTokens(id=1, access_token=access_token, refresh_token=refresh_token))
            await session.commit()
    except Exception as exc:
        print(f"[TokenStore] Error al guardar tokens: {exc}")
