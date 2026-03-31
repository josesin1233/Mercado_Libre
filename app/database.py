"""Configuración de base de datos — SQLAlchemy async con PostgreSQL."""

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Integer, Text, DateTime, func
from datetime import datetime

from app.config import settings


class Base(DeclarativeBase):
    pass


class PedidoProduccion(Base):
    __tablename__ = "pedidos_produccion"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cliente: Mapped[str | None] = mapped_column(String(200), nullable=True)
    producto: Mapped[str] = mapped_column(String(200), nullable=False)
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False)
    estado: Mapped[str] = mapped_column(String(50), nullable=False, default="pendiente")
    imagen_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    fecha_entrega: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)


# Estado válidos y su label visual
ESTADOS = {
    "pendiente":  ("Pendiente",   "badge-warning"),
    "en_proceso": ("En proceso",  "badge-info"),
    "listo":      ("Listo",       "badge-success"),
    "entregado":  ("Entregado",   "badge-neutral"),
}

ESTADOS_ORDEN = list(ESTADOS.keys())  # orden de progreso


def _make_engine():
    url = settings.DATABASE_URL
    if not url:
        raise RuntimeError(
            "DATABASE_URL no configurada. "
            "Agrega postgresql+asyncpg://user:pass@host:port/db en tu .env"
        )
    return create_async_engine(url, echo=False, pool_pre_ping=True)


# Engine y session factory se crean al primer uso (lazy)
_engine = None
_session_factory = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = _make_engine()
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    return _session_factory


async def init_db():
    """Crea las tablas si no existen. Llamar en el lifespan de la app."""
    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
