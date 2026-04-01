"""Configuración de base de datos — SQLAlchemy async con PostgreSQL."""

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Integer, Text, DateTime, func, text
from datetime import datetime

from app.config import settings


class Base(DeclarativeBase):
    pass


class Artista(Base):
    __tablename__ = "artistas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)


class PedidoProduccion(Base):
    __tablename__ = "pedidos_produccion"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    album: Mapped[str] = mapped_column(String(200), nullable=False)
    artista: Mapped[str | None] = mapped_column(String(200), nullable=True)
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False)
    estado: Mapped[str] = mapped_column(String(50), nullable=False, default="diseno")
    imagen_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    # Fechas por objetivo (solo las del estado inicial en adelante)
    fecha_diseno: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fecha_impresion: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fecha_limpiado: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fecha_clavado: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Fecha de entrega final (obligatoria)
    fecha_entrega: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Recordatorios adicionales (texto libre; en el futuro: JSON para Telegram)
    recordatorios: Mapped[str | None] = mapped_column(Text, nullable=True)
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)


# Estados en orden de progreso
ESTADOS_ORDEN = ["diseno", "impresion", "limpiado", "clavado"]

ESTADOS = {
    "diseno":    ("Diseño",    "badge-info"),
    "impresion": ("Impresión", "badge-warning"),
    "limpiado":  ("Limpiado",  "badge-success"),
    "clavado":   ("Clavado",   "badge-neutral"),
}


def _make_engine():
    url = settings.DATABASE_URL
    if not url:
        raise RuntimeError(
            "DATABASE_URL no configurada. "
            "Agrega postgresql+asyncpg://user:pass@host:port/db en tu .env"
        )
    return create_async_engine(url, echo=False, pool_pre_ping=True)


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
    """Crea tablas nuevas y aplica migraciones sobre tablas existentes."""
    async with get_engine().begin() as conn:
        # Crea tablas que no existan (artistas es nueva, pedidos_produccion puede existir)
        await conn.run_sync(Base.metadata.create_all)

        # Migraciones: agrega columnas nuevas si no existen (safe en PostgreSQL)
        migrations = [
            "ALTER TABLE pedidos_produccion ADD COLUMN IF NOT EXISTS album VARCHAR(200);",
            "ALTER TABLE pedidos_produccion ADD COLUMN IF NOT EXISTS artista VARCHAR(200);",
            "ALTER TABLE pedidos_produccion ADD COLUMN IF NOT EXISTS fecha_diseno TIMESTAMPTZ;",
            "ALTER TABLE pedidos_produccion ADD COLUMN IF NOT EXISTS fecha_impresion TIMESTAMPTZ;",
            "ALTER TABLE pedidos_produccion ADD COLUMN IF NOT EXISTS fecha_limpiado TIMESTAMPTZ;",
            "ALTER TABLE pedidos_produccion ADD COLUMN IF NOT EXISTS fecha_clavado TIMESTAMPTZ;",
            "ALTER TABLE pedidos_produccion ADD COLUMN IF NOT EXISTS recordatorios TEXT;",
            # Si existe la columna 'producto' (versión anterior), copia a album y renombra
            """
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name='pedidos_produccion' AND column_name='producto'
                ) THEN
                    UPDATE pedidos_produccion SET album = producto WHERE album IS NULL;
                    ALTER TABLE pedidos_produccion DROP COLUMN IF EXISTS producto;
                END IF;
            END $$;
            """,
            # Si existe columna 'cliente' de versión anterior, eliminarla
            "ALTER TABLE pedidos_produccion DROP COLUMN IF EXISTS cliente;",
            # Asegurar que album tenga NOT NULL donde sea posible
            "UPDATE pedidos_produccion SET album = 'Sin título' WHERE album IS NULL OR album = '';",
        ]
        for stmt in migrations:
            await conn.execute(text(stmt))
