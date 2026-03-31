"""Módulo de producción — pedidos externos con upload de imagen."""

import os
import uuid
import mimetypes
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse, JSONResponse
from sqlalchemy import select, update

from app.database import PedidoProduccion, ESTADOS, ESTADOS_ORDEN, get_session_factory
from app.ui import base_layout

router = APIRouter()

UPLOADS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "uploads")
os.makedirs(UPLOADS_DIR, exist_ok=True)

ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_SIZE_MB = 10


# ── CSS específico de producción ─────────────────────────────────────────────

PRODUCCION_CSS = """
/* ── Producción page ── */
.prod-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin: 28px 0 20px;
    flex-wrap: wrap;
    gap: 12px;
}

.prod-header h1 {
    font-size: 22px;
    font-weight: 700;
    color: var(--text);
    letter-spacing: -0.4px;
}

.prod-controls {
    display: flex;
    gap: 10px;
    align-items: center;
    flex-wrap: wrap;
}

.sort-select {
    padding: 7px 12px;
    border: 1px solid var(--border-strong);
    border-radius: var(--radius-sm);
    background: var(--surface);
    color: var(--text);
    font-size: 13px;
    cursor: pointer;
    outline: none;
}

.sort-select:focus { border-color: var(--accent); }

/* Tabla */
.prod-table-wrap {
    background: var(--surface);
    border-radius: var(--radius);
    border: 1px solid var(--border);
    box-shadow: var(--shadow);
    overflow: hidden;
}

.prod-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13.5px;
}

.prod-table thead th {
    background: var(--surface-2);
    color: var(--text-secondary);
    font-weight: 600;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    padding: 12px 16px;
    text-align: left;
    border-bottom: 1px solid var(--border);
    white-space: nowrap;
    cursor: pointer;
    user-select: none;
}

.prod-table thead th:hover { color: var(--text); }
.prod-table thead th .sort-icon { margin-left: 4px; opacity: 0.4; }
.prod-table thead th.sorted .sort-icon { opacity: 1; color: var(--accent); }

.prod-table tbody tr {
    border-bottom: 1px solid var(--border);
    transition: background var(--transition);
}
.prod-table tbody tr:last-child { border-bottom: none; }
.prod-table tbody tr:hover { background: var(--surface-hover); }

.prod-table td {
    padding: 13px 16px;
    vertical-align: middle;
    color: var(--text);
}

.prod-table td.td-img {
    width: 56px;
    padding: 8px 12px;
}

.prod-thumb {
    width: 44px;
    height: 44px;
    object-fit: cover;
    border-radius: var(--radius-sm);
    border: 1px solid var(--border);
    cursor: pointer;
    transition: transform var(--transition);
}
.prod-thumb:hover { transform: scale(1.08); }
.prod-thumb-placeholder {
    width: 44px;
    height: 44px;
    border-radius: var(--radius-sm);
    border: 1px dashed var(--border-strong);
    background: var(--surface-2);
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--text-muted);
    font-size: 18px;
}

.prod-producto { font-weight: 600; color: var(--text); }
.prod-cliente  { color: var(--text-secondary); font-size: 13px; }

.qty-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    background: var(--surface-2);
    border: 1px solid var(--border);
    border-radius: 20px;
    padding: 3px 10px;
    font-weight: 600;
    font-size: 13px;
    min-width: 36px;
}

.badge-warning  { background: var(--warning-bg);  color: var(--warning-text);  border: 1px solid #fde68a; }
.badge-info     { background: var(--info-bg);     color: var(--info-text);     border: 1px solid #a5f3fc; }
.badge-success  { background: var(--success-bg);  color: var(--success-text);  border: 1px solid #a7f3d0; }
.badge-neutral  { background: var(--surface-2);   color: var(--text-secondary);border: 1px solid var(--border); }

.status-badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.2px;
}

.td-fecha { color: var(--text-secondary); font-size: 13px; white-space: nowrap; }
.td-fecha.vencida { color: var(--danger); font-weight: 600; }

.td-actions {
    display: flex;
    gap: 6px;
    align-items: center;
}

.btn-status {
    padding: 4px 10px;
    border-radius: var(--radius-sm);
    border: 1px solid var(--border-strong);
    background: var(--surface);
    color: var(--text-secondary);
    font-size: 12px;
    cursor: pointer;
    transition: all var(--transition);
}
.btn-status:hover { background: var(--accent); color: #fff; border-color: var(--accent); }

.btn-delete {
    padding: 4px 8px;
    border-radius: var(--radius-sm);
    border: 1px solid transparent;
    background: transparent;
    color: var(--text-muted);
    font-size: 14px;
    cursor: pointer;
    transition: all var(--transition);
}
.btn-delete:hover { background: var(--danger-bg); color: var(--danger); }

/* Empty state */
.prod-empty {
    text-align: center;
    padding: 60px 20px;
    color: var(--text-muted);
}
.prod-empty .empty-icon { font-size: 40px; margin-bottom: 12px; }
.prod-empty p { font-size: 15px; }

/* Modal nuevo pedido */
.modal-overlay {
    display: none;
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.45);
    z-index: 500;
    align-items: center;
    justify-content: center;
}
.modal-overlay.open { display: flex; }

.modal-box {
    background: var(--surface);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-xl);
    width: 100%;
    max-width: 520px;
    margin: 16px;
    animation: modalIn 0.18s ease;
    max-height: 90vh;
    overflow-y: auto;
}
@keyframes modalIn {
    from { opacity: 0; transform: translateY(12px) scale(0.98); }
    to   { opacity: 1; transform: translateY(0) scale(1); }
}

.modal-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 20px 24px 0;
}
.modal-header h2 { font-size: 17px; font-weight: 700; }
.modal-close {
    background: none;
    border: none;
    font-size: 22px;
    color: var(--text-muted);
    cursor: pointer;
    line-height: 1;
    padding: 4px;
    border-radius: var(--radius-sm);
    transition: color var(--transition);
}
.modal-close:hover { color: var(--text); }

.modal-form { padding: 20px 24px 24px; display: flex; flex-direction: column; gap: 16px; }

.form-group { display: flex; flex-direction: column; gap: 6px; }
.form-group label { font-size: 13px; font-weight: 600; color: var(--text-secondary); }

.form-input, .form-select, .form-textarea {
    padding: 9px 12px;
    border: 1px solid var(--border-strong);
    border-radius: var(--radius-sm);
    background: var(--surface);
    color: var(--text);
    font-size: 14px;
    outline: none;
    transition: border-color var(--transition);
    font-family: inherit;
}
.form-input:focus, .form-select:focus, .form-textarea:focus {
    border-color: var(--accent);
    box-shadow: 0 0 0 3px rgba(45,114,217,0.1);
}

.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }

/* Upload zone */
.upload-zone {
    border: 2px dashed var(--border-strong);
    border-radius: var(--radius);
    padding: 24px;
    text-align: center;
    cursor: pointer;
    transition: all var(--transition);
    background: var(--surface-2);
    position: relative;
}
.upload-zone:hover, .upload-zone.drag-over {
    border-color: var(--accent);
    background: var(--accent-soft);
}
.upload-zone input[type=file] {
    position: absolute;
    inset: 0;
    opacity: 0;
    cursor: pointer;
    width: 100%;
    height: 100%;
}
.upload-icon { font-size: 28px; margin-bottom: 8px; }
.upload-label { font-size: 13.5px; color: var(--text-secondary); }
.upload-label strong { color: var(--accent); }
.upload-hint { font-size: 12px; color: var(--text-muted); margin-top: 4px; }
.upload-preview {
    display: none;
    margin-top: 10px;
    max-width: 100%;
    max-height: 160px;
    border-radius: var(--radius-sm);
    object-fit: contain;
}

.form-actions { display: flex; gap: 10px; justify-content: flex-end; margin-top: 4px; }
.btn-cancel {
    padding: 9px 18px;
    border: 1px solid var(--border-strong);
    border-radius: var(--radius-sm);
    background: var(--surface);
    color: var(--text-secondary);
    font-size: 14px;
    cursor: pointer;
    font-family: inherit;
    transition: all var(--transition);
}
.btn-cancel:hover { background: var(--surface-hover); }
.btn-submit {
    padding: 9px 22px;
    border: none;
    border-radius: var(--radius-sm);
    background: var(--accent);
    color: #fff;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    font-family: inherit;
    transition: background var(--transition);
}
.btn-submit:hover { background: var(--accent-hover); }

/* Image lightbox */
.lightbox {
    display: none;
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.85);
    z-index: 600;
    align-items: center;
    justify-content: center;
}
.lightbox.open { display: flex; }
.lightbox img {
    max-width: 90vw;
    max-height: 90vh;
    border-radius: var(--radius);
    object-fit: contain;
}
.lightbox-close {
    position: absolute;
    top: 20px;
    right: 24px;
    color: #fff;
    font-size: 32px;
    cursor: pointer;
    background: none;
    border: none;
    line-height: 1;
}
"""


# ── Helpers HTML ─────────────────────────────────────────────────────────────

def _format_fecha(dt: datetime | None) -> tuple[str, bool]:
    """Devuelve (texto, es_vencida)."""
    if dt is None:
        return "—", False
    now = datetime.now(tz=dt.tzinfo)
    vencida = dt < now
    return dt.strftime("%d/%m/%Y"), vencida


def _build_table(pedidos: list[PedidoProduccion]) -> str:
    if not pedidos:
        return """
        <div class="prod-empty">
            <div class="empty-icon">📋</div>
            <p>No hay pedidos de producción aún.<br>Crea el primero con el botón de arriba.</p>
        </div>"""

    rows = ""
    for p in pedidos:
        estado_label, estado_cls = ESTADOS.get(p.estado, (p.estado, "badge-neutral"))
        fecha_txt, vencida = _format_fecha(p.fecha_entrega)
        fecha_cls = "td-fecha vencida" if vencida else "td-fecha"

        if p.imagen_path:
            img_url = f"/produccion/uploads/{os.path.basename(p.imagen_path)}"
            img_html = f'<img src="{img_url}" class="prod-thumb" onclick="openLightbox(\'{img_url}\')" title="Ver imagen">'
        else:
            img_html = '<div class="prod-thumb-placeholder">🖼</div>'

        cliente_html = f'<div class="prod-cliente">{p.cliente}</div>' if p.cliente else ""

        # Botón avanzar estado
        idx = ESTADOS_ORDEN.index(p.estado) if p.estado in ESTADOS_ORDEN else -1
        next_estado = ESTADOS_ORDEN[idx + 1] if idx >= 0 and idx < len(ESTADOS_ORDEN) - 1 else None
        avanzar_btn = ""
        if next_estado:
            next_label = ESTADOS[next_estado][0]
            avanzar_btn = f"""
            <button class="btn-status"
                onclick="cambiarEstado({p.id}, '{next_estado}')"
                title="Marcar como {next_label}">
                → {next_label}
            </button>"""

        rows += f"""
        <tr id="row-{p.id}">
            <td class="td-img">{img_html}</td>
            <td>
                <div class="prod-producto">{p.producto}</div>
                {cliente_html}
            </td>
            <td><span class="qty-badge">{p.cantidad}</span></td>
            <td>
                <span class="status-badge {estado_cls}" id="badge-{p.id}">{estado_label}</span>
            </td>
            <td class="{fecha_cls}">{fecha_txt}</td>
            <td>
                <div class="td-actions">
                    {avanzar_btn}
                    <button class="btn-delete"
                        onclick="eliminarPedido({p.id})"
                        title="Eliminar">✕</button>
                </div>
            </td>
        </tr>"""

    return f"""
    <div class="prod-table-wrap">
        <table class="prod-table" id="prodTable">
            <thead>
                <tr>
                    <th></th>
                    <th onclick="sortTable('producto')" id="th-producto">
                        Producto <span class="sort-icon">↕</span>
                    </th>
                    <th onclick="sortTable('cantidad')" id="th-cantidad">
                        Cantidad <span class="sort-icon">↕</span>
                    </th>
                    <th onclick="sortTable('estado')" id="th-estado">
                        Estado <span class="sort-icon">↕</span>
                    </th>
                    <th onclick="sortTable('fecha')" id="th-fecha">
                        Entrega <span class="sort-icon">↕</span>
                    </th>
                    <th>Acciones</th>
                </tr>
            </thead>
            <tbody id="prodTbody">
                {rows}
            </tbody>
        </table>
    </div>"""


def _build_modal() -> str:
    estados_opts = "".join(
        f'<option value="{k}">{v[0]}</option>' for k, v in ESTADOS.items()
    )
    return f"""
    <div class="modal-overlay" id="nuevoModal">
        <div class="modal-box">
            <div class="modal-header">
                <h2>Nuevo pedido de producción</h2>
                <button class="modal-close" onclick="closeModal()">×</button>
            </div>
            <form class="modal-form" id="nuevoForm"
                  method="POST" action="/produccion/nuevo"
                  enctype="multipart/form-data">

                <div class="form-group">
                    <label>Imagen del diseño</label>
                    <div class="upload-zone" id="uploadZone">
                        <input type="file" name="imagen" id="imagenInput"
                               accept="image/*" onchange="previewImage(this)">
                        <div class="upload-icon">📁</div>
                        <div class="upload-label">
                            <strong>Selecciona una imagen</strong> o arrastra aquí
                        </div>
                        <div class="upload-hint">JPG, PNG, WEBP — máx. 10 MB</div>
                        <img id="uploadPreview" class="upload-preview">
                    </div>
                </div>

                <div class="form-group">
                    <label for="producto">Nombre del producto *</label>
                    <input type="text" name="producto" id="producto"
                           class="form-input" placeholder="Ej. Playera estampada" required>
                </div>

                <div class="form-row">
                    <div class="form-group">
                        <label for="cantidad">Cantidad *</label>
                        <input type="number" name="cantidad" id="cantidad"
                               class="form-input" min="1" placeholder="1" required>
                    </div>
                    <div class="form-group">
                        <label for="estado">Estado inicial</label>
                        <select name="estado" id="estado" class="form-select">
                            {estados_opts}
                        </select>
                    </div>
                </div>

                <div class="form-row">
                    <div class="form-group">
                        <label for="cliente">Cliente</label>
                        <input type="text" name="cliente" id="cliente"
                               class="form-input" placeholder="Nombre del cliente">
                    </div>
                    <div class="form-group">
                        <label for="fecha_entrega">Fecha de entrega</label>
                        <input type="date" name="fecha_entrega" id="fecha_entrega"
                               class="form-input">
                    </div>
                </div>

                <div class="form-group">
                    <label for="notas">Notas</label>
                    <textarea name="notas" id="notas" class="form-textarea"
                              rows="2" placeholder="Detalles adicionales..."></textarea>
                </div>

                <div class="form-actions">
                    <button type="button" class="btn-cancel" onclick="closeModal()">Cancelar</button>
                    <button type="submit" class="btn-submit">Crear pedido</button>
                </div>
            </form>
        </div>
    </div>

    <!-- Lightbox para imágenes -->
    <div class="lightbox" id="lightbox" onclick="closeLightbox()">
        <button class="lightbox-close" onclick="closeLightbox()">×</button>
        <img id="lightboxImg" src="">
    </div>"""


def _build_js() -> str:
    return """
    <script>
    // ── Modal ──
    function openModal() {
        document.getElementById('nuevoModal').classList.add('open');
    }
    function closeModal() {
        document.getElementById('nuevoModal').classList.remove('open');
    }
    document.getElementById('nuevoModal').addEventListener('click', function(e) {
        if (e.target === this) closeModal();
    });
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') { closeModal(); closeLightbox(); }
    });

    // ── Upload preview ──
    function previewImage(input) {
        const preview = document.getElementById('uploadPreview');
        if (input.files && input.files[0]) {
            const reader = new FileReader();
            reader.onload = e => {
                preview.src = e.target.result;
                preview.style.display = 'block';
            };
            reader.readAsDataURL(input.files[0]);
        }
    }

    // Drag-over visual
    const zone = document.getElementById('uploadZone');
    if (zone) {
        zone.addEventListener('dragover', () => zone.classList.add('drag-over'));
        zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
        zone.addEventListener('drop', () => zone.classList.remove('drag-over'));
    }

    // ── Lightbox ──
    function openLightbox(src) {
        document.getElementById('lightboxImg').src = src;
        document.getElementById('lightbox').classList.add('open');
    }
    function closeLightbox() {
        document.getElementById('lightbox').classList.remove('open');
    }

    // ── Cambiar estado vía AJAX ──
    async function cambiarEstado(id, nuevoEstado) {
        const res = await fetch(`/produccion/${id}/status`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ estado: nuevoEstado })
        });
        if (res.ok) {
            location.reload();
        } else {
            alert('Error al actualizar el estado');
        }
    }

    // ── Eliminar pedido ──
    async function eliminarPedido(id) {
        if (!confirm('¿Eliminar este pedido?')) return;
        const res = await fetch(`/produccion/${id}`, { method: 'DELETE' });
        if (res.ok) {
            const row = document.getElementById('row-' + id);
            if (row) row.remove();
        } else {
            alert('Error al eliminar');
        }
    }

    // ── Ordenar tabla client-side ──
    let sortState = { col: null, asc: true };

    function sortTable(col) {
        const tbody = document.getElementById('prodTbody');
        if (!tbody) return;
        const rows = Array.from(tbody.querySelectorAll('tr'));

        if (sortState.col === col) {
            sortState.asc = !sortState.asc;
        } else {
            sortState.col = col;
            sortState.asc = true;
        }

        // Actualizar iconos
        document.querySelectorAll('.prod-table thead th').forEach(th => th.classList.remove('sorted'));
        const thMap = { producto: 'th-producto', cantidad: 'th-cantidad', estado: 'th-estado', fecha: 'th-fecha' };
        const activeTh = document.getElementById(thMap[col]);
        if (activeTh) {
            activeTh.classList.add('sorted');
            activeTh.querySelector('.sort-icon').textContent = sortState.asc ? '↑' : '↓';
        }

        const colIndex = { producto: 1, cantidad: 2, estado: 3, fecha: 4 };
        const idx = colIndex[col];

        rows.sort((a, b) => {
            const aVal = a.cells[idx]?.textContent.trim() ?? '';
            const bVal = b.cells[idx]?.textContent.trim() ?? '';
            if (col === 'cantidad') {
                return sortState.asc
                    ? parseInt(aVal) - parseInt(bVal)
                    : parseInt(bVal) - parseInt(aVal);
            }
            return sortState.asc
                ? aVal.localeCompare(bVal, 'es')
                : bVal.localeCompare(aVal, 'es');
        });

        rows.forEach(r => tbody.appendChild(r));
    }
    </script>"""


def _page(pedidos: list[PedidoProduccion], sort: str, order: str) -> str:
    table_html = _build_table(pedidos)
    modal_html = _build_modal()
    js_html = _build_js()

    sort_opts = [
        ("fecha_creacion", "Más recientes"),
        ("fecha_entrega", "Fecha de entrega"),
        ("cantidad", "Cantidad"),
        ("estado", "Estado"),
        ("producto", "Nombre"),
    ]
    opts_html = "".join(
        f'<option value="{v}" {"selected" if v == sort else ""}>{l}</option>'
        for v, l in sort_opts
    )
    order_opts = (
        f'<option value="asc" {"selected" if order=="asc" else ""}>Ascendente</option>'
        f'<option value="desc" {"selected" if order=="desc" else ""}>Descendente</option>'
    )

    content = f"""
    <style>{PRODUCCION_CSS}</style>

    <div class="prod-header">
        <h1>Pedidos de producción</h1>
        <div class="prod-controls">
            <select class="sort-select" id="sortBy" onchange="applySort()">
                {opts_html}
            </select>
            <select class="sort-select" id="sortOrder" onchange="applySort()">
                {order_opts}
            </select>
            <button class="btn" onclick="openModal()">+ Nuevo pedido</button>
        </div>
    </div>

    {table_html}
    {modal_html}

    <script>
    function applySort() {{
        const s = document.getElementById('sortBy').value;
        const o = document.getElementById('sortOrder').value;
        window.location.href = `/produccion/?sort=${{s}}&order=${{o}}`;
    }}
    </script>
    {js_html}
    """
    return base_layout("Producción", content, active="produccion")


# ── Routes ───────────────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
async def produccion_index(sort: str = "fecha_creacion", order: str = "desc"):
    session_factory = get_session_factory()
    async with session_factory() as session:
        col_map = {
            "fecha_creacion": PedidoProduccion.fecha_creacion,
            "fecha_entrega":  PedidoProduccion.fecha_entrega,
            "cantidad":       PedidoProduccion.cantidad,
            "estado":         PedidoProduccion.estado,
            "producto":       PedidoProduccion.producto,
        }
        col = col_map.get(sort, PedidoProduccion.fecha_creacion)
        direction = col.desc() if order == "desc" else col.asc()
        result = await session.execute(select(PedidoProduccion).order_by(direction))
        pedidos = result.scalars().all()

    return _page(list(pedidos), sort, order)


@router.post("/nuevo")
async def crear_pedido(
    producto: str = Form(...),
    cantidad: int = Form(...),
    estado: str = Form("pendiente"),
    cliente: str = Form(""),
    fecha_entrega: str = Form(""),
    notas: str = Form(""),
    imagen: UploadFile = File(None),
):
    imagen_path = None

    if imagen and imagen.filename:
        content_type = imagen.content_type or mimetypes.guess_type(imagen.filename)[0] or ""
        if content_type not in ALLOWED_MIME:
            return JSONResponse(status_code=400, content={"detail": "Tipo de imagen no permitido"})

        data = await imagen.read()
        if len(data) > MAX_SIZE_MB * 1024 * 1024:
            return JSONResponse(status_code=400, content={"detail": f"Imagen supera {MAX_SIZE_MB} MB"})

        ext = os.path.splitext(imagen.filename)[1].lower() or ".jpg"
        filename = f"{uuid.uuid4().hex}{ext}"
        imagen_path = os.path.join(UPLOADS_DIR, filename)
        with open(imagen_path, "wb") as f:
            f.write(data)

    fecha_dt = None
    if fecha_entrega:
        try:
            fecha_dt = datetime.fromisoformat(fecha_entrega)
        except ValueError:
            pass

    pedido = PedidoProduccion(
        producto=producto.strip(),
        cantidad=cantidad,
        estado=estado if estado in ESTADOS else "pendiente",
        cliente=cliente.strip() or None,
        fecha_entrega=fecha_dt,
        notas=notas.strip() or None,
        imagen_path=imagen_path,
    )

    session_factory = get_session_factory()
    async with session_factory() as session:
        session.add(pedido)
        await session.commit()

    return RedirectResponse("/produccion/", status_code=303)


@router.post("/{pedido_id}/status")
async def actualizar_estado(pedido_id: int, request: Request):
    body = await request.json()
    nuevo_estado = body.get("estado", "")
    if nuevo_estado not in ESTADOS:
        return JSONResponse(status_code=400, content={"detail": "Estado inválido"})

    session_factory = get_session_factory()
    async with session_factory() as session:
        await session.execute(
            update(PedidoProduccion)
            .where(PedidoProduccion.id == pedido_id)
            .values(estado=nuevo_estado)
        )
        await session.commit()

    return JSONResponse({"ok": True})


@router.delete("/{pedido_id}")
async def eliminar_pedido(pedido_id: int):
    session_factory = get_session_factory()
    async with session_factory() as session:
        result = await session.execute(
            select(PedidoProduccion).where(PedidoProduccion.id == pedido_id)
        )
        pedido = result.scalar_one_or_none()
        if not pedido:
            return JSONResponse(status_code=404, content={"detail": "No encontrado"})

        # Borrar imagen del disco si existe
        if pedido.imagen_path and os.path.exists(pedido.imagen_path):
            os.remove(pedido.imagen_path)

        await session.delete(pedido)
        await session.commit()

    return JSONResponse({"ok": True})


@router.get("/uploads/{filename}")
async def serve_upload(filename: str):
    # Prevenir path traversal
    safe_name = os.path.basename(filename)
    path = os.path.join(UPLOADS_DIR, safe_name)
    if not os.path.exists(path):
        return JSONResponse(status_code=404, content={"detail": "Imagen no encontrada"})
    return FileResponse(path)
