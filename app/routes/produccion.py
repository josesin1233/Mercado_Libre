"""Módulo de producción — pedidos externos con upload de imagen."""

import os
import uuid
import mimetypes
from datetime import datetime, timezone

from fastapi import APIRouter, UploadFile, File, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse, JSONResponse
from sqlalchemy import select, update, delete

from app.database import (
    PedidoProduccion, Artista,
    ESTADOS, ESTADOS_ORDEN,
    get_session_factory,
)
from app.ui import base_layout

router = APIRouter()

UPLOADS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "uploads")
os.makedirs(UPLOADS_DIR, exist_ok=True)

ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_SIZE_MB = 10


# ── CSS ──────────────────────────────────────────────────────────────────────

PRODUCCION_CSS = """
.prod-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin: 28px 0 16px;
    flex-wrap: wrap;
    gap: 12px;
}
.prod-header h1 { font-size: 22px; font-weight: 700; letter-spacing: -0.4px; }

.prod-toolbar {
    display: flex;
    gap: 10px;
    align-items: center;
    flex-wrap: wrap;
    margin-bottom: 20px;
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

.clientes-placeholder {
    margin-left: auto;
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 14px;
    border: 1px dashed var(--border-strong);
    border-radius: var(--radius-sm);
    background: var(--surface-2);
    color: var(--text-muted);
    font-size: 12.5px;
    font-weight: 500;
}
.clientes-placeholder span { font-size: 15px; }

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
    font-size: 11.5px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    padding: 11px 14px;
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
.prod-table td { padding: 12px 14px; vertical-align: middle; }

.td-img { width: 52px; padding: 8px 10px !important; }
.prod-thumb {
    width: 42px; height: 42px;
    object-fit: cover;
    border-radius: var(--radius-sm);
    border: 1px solid var(--border);
    cursor: pointer;
    transition: transform var(--transition);
}
.prod-thumb:hover { transform: scale(1.1); }
.prod-thumb-placeholder {
    width: 42px; height: 42px;
    border-radius: var(--radius-sm);
    border: 1px dashed var(--border-strong);
    background: var(--surface-2);
    display: flex; align-items: center; justify-content: center;
    color: var(--text-muted); font-size: 16px;
}

.td-album strong { font-weight: 600; display: block; }
.td-album span { font-size: 12.5px; color: var(--text-secondary); }

.qty-badge {
    display: inline-flex; align-items: center; justify-content: center;
    background: var(--surface-2);
    border: 1px solid var(--border);
    border-radius: 20px;
    padding: 3px 10px;
    font-weight: 600; font-size: 13px; min-width: 36px;
}

/* Timeline de estados */
.timeline {
    display: flex;
    align-items: center;
    gap: 0;
    min-width: 220px;
}
.tl-step {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 4px;
    position: relative;
    flex: 1;
}
.tl-dot {
    width: 22px; height: 22px;
    border-radius: 50%;
    border: 2px solid var(--border-strong);
    background: var(--surface);
    display: flex; align-items: center; justify-content: center;
    font-size: 10px;
    cursor: pointer;
    transition: all var(--transition);
    position: relative;
    z-index: 1;
}
.tl-dot:hover { border-color: var(--accent); transform: scale(1.15); }
.tl-dot.done {
    background: var(--success);
    border-color: var(--success);
    color: #fff;
}
.tl-dot.active {
    background: var(--accent);
    border-color: var(--accent);
    color: #fff;
    box-shadow: 0 0 0 3px rgba(45,114,217,0.2);
}
.tl-label {
    font-size: 10px;
    color: var(--text-muted);
    white-space: nowrap;
    font-weight: 500;
}
.tl-label.done  { color: var(--success-text); }
.tl-label.active { color: var(--accent); font-weight: 600; }

.tl-line {
    flex: 1;
    height: 2px;
    background: var(--border);
    margin-bottom: 14px;
    transition: background var(--transition);
}
.tl-line.done { background: var(--success); }

/* Fecha entrega + días */
.td-fecha { font-size: 13px; white-space: nowrap; }
.dias-badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 11.5px;
    font-weight: 600;
    margin-top: 3px;
}
.dias-ok      { background: var(--success-bg); color: var(--success-text); }
.dias-warn    { background: var(--warning-bg); color: var(--warning-text); }
.dias-vencida { background: var(--danger-bg);  color: var(--danger-text); }
.dias-none    { color: var(--text-muted); font-size: 12px; }

.td-actions { display: flex; gap: 6px; align-items: center; }
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
.prod-empty { text-align: center; padding: 60px 20px; color: var(--text-muted); }
.prod-empty .empty-icon { font-size: 40px; margin-bottom: 12px; }
.prod-empty p { font-size: 15px; }

/* Modal */
.modal-overlay {
    display: none; position: fixed; inset: 0;
    background: rgba(0,0,0,0.45);
    z-index: 500; align-items: center; justify-content: center;
}
.modal-overlay.open { display: flex; }
.modal-box {
    background: var(--surface);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-xl);
    width: 100%; max-width: 540px;
    margin: 16px;
    animation: modalIn 0.18s ease;
    max-height: 92vh; overflow-y: auto;
}
@keyframes modalIn {
    from { opacity:0; transform: translateY(12px) scale(0.98); }
    to   { opacity:1; transform: translateY(0) scale(1); }
}
.modal-header {
    display: flex; align-items: center; justify-content: space-between;
    padding: 20px 24px 0;
    position: sticky; top: 0; background: var(--surface); z-index: 1;
    padding-bottom: 12px; border-bottom: 1px solid var(--border);
}
.modal-header h2 { font-size: 17px; font-weight: 700; }
.modal-close {
    background: none; border: none; font-size: 22px;
    color: var(--text-muted); cursor: pointer;
    line-height: 1; padding: 4px; border-radius: var(--radius-sm);
    transition: color var(--transition);
}
.modal-close:hover { color: var(--text); }

.modal-form { padding: 20px 24px 24px; display: flex; flex-direction: column; gap: 14px; }
.form-section-title {
    font-size: 11px; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.6px; color: var(--text-muted);
    border-bottom: 1px solid var(--border); padding-bottom: 6px;
    margin-bottom: -4px;
}
.form-group { display: flex; flex-direction: column; gap: 5px; }
.form-group label { font-size: 13px; font-weight: 600; color: var(--text-secondary); }
.form-input, .form-select, .form-textarea {
    padding: 9px 12px;
    border: 1px solid var(--border-strong);
    border-radius: var(--radius-sm);
    background: var(--surface);
    color: var(--text); font-size: 14px; outline: none;
    transition: border-color var(--transition); font-family: inherit;
}
.form-input:focus, .form-select:focus, .form-textarea:focus {
    border-color: var(--accent);
    box-shadow: 0 0 0 3px rgba(45,114,217,0.1);
}
.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.form-hint { font-size: 11.5px; color: var(--text-muted); margin-top: -2px; }

/* Fechas por objetivo */
.fechas-grid {
    display: flex; flex-direction: column; gap: 10px;
    padding: 12px 14px;
    background: var(--surface-2);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
}
.fecha-row {
    display: flex; align-items: center; gap: 10px;
}
.fecha-row .tl-dot-mini {
    width: 18px; height: 18px; border-radius: 50%;
    border: 2px solid var(--border-strong);
    background: var(--surface); flex-shrink: 0;
}
.fecha-row label { font-size: 13px; font-weight: 500; color: var(--text); min-width: 90px; }
.fecha-row .form-input { flex: 1; padding: 7px 10px; font-size: 13px; }
.fecha-row.hidden { display: none; }

/* Upload */
.upload-zone {
    border: 2px dashed var(--border-strong);
    border-radius: var(--radius);
    padding: 20px; text-align: center; cursor: pointer;
    transition: all var(--transition);
    background: var(--surface-2); position: relative;
}
.upload-zone:hover, .upload-zone.drag-over {
    border-color: var(--accent); background: var(--accent-soft);
}
.upload-zone input[type=file] {
    position: absolute; inset: 0; opacity: 0; cursor: pointer;
    width: 100%; height: 100%;
}
.upload-icon { font-size: 26px; margin-bottom: 6px; }
.upload-label { font-size: 13px; color: var(--text-secondary); }
.upload-label strong { color: var(--accent); }
.upload-hint { font-size: 11.5px; color: var(--text-muted); margin-top: 3px; }
.upload-preview {
    display: none; margin-top: 10px;
    max-width: 100%; max-height: 140px;
    border-radius: var(--radius-sm); object-fit: contain;
}

.form-actions { display: flex; gap: 10px; justify-content: flex-end; margin-top: 4px; }
.btn-cancel {
    padding: 9px 18px; border: 1px solid var(--border-strong);
    border-radius: var(--radius-sm); background: var(--surface);
    color: var(--text-secondary); font-size: 14px; cursor: pointer;
    font-family: inherit; transition: all var(--transition);
}
.btn-cancel:hover { background: var(--surface-hover); }
.btn-submit {
    padding: 9px 22px; border: none; border-radius: var(--radius-sm);
    background: var(--accent); color: #fff; font-size: 14px;
    font-weight: 600; cursor: pointer; font-family: inherit;
    transition: background var(--transition);
}
.btn-submit:hover { background: var(--accent-hover); }

/* Lightbox */
.lightbox {
    display: none; position: fixed; inset: 0;
    background: rgba(0,0,0,0.85); z-index: 600;
    align-items: center; justify-content: center;
}
.lightbox.open { display: flex; }
.lightbox img { max-width: 90vw; max-height: 90vh; border-radius: var(--radius); object-fit: contain; }
.lightbox-close {
    position: absolute; top: 20px; right: 24px;
    color: #fff; font-size: 32px; cursor: pointer;
    background: none; border: none; line-height: 1;
}

/* Badge clases reutilizadas */
.badge-info    { background: var(--info-bg);    color: var(--info-text);    border: 1px solid #a5f3fc; }
.badge-warning { background: var(--warning-bg); color: var(--warning-text); border: 1px solid #fde68a; }
.badge-success { background: var(--success-bg); color: var(--success-text); border: 1px solid #a7f3d0; }
.badge-neutral { background: var(--surface-2);  color: var(--text-secondary);border: 1px solid var(--border); }
"""


# ── Helpers ───────────────────────────────────────────────────────────────────

def _days_remaining(fecha: datetime | None) -> tuple[str, str]:
    """Devuelve (texto_días, css_class)."""
    if fecha is None:
        return "—", "dias-none"
    now = datetime.now(tz=fecha.tzinfo or timezone.utc)
    delta = (fecha.date() - now.date()).days
    if delta < 0:
        return f"Hace {abs(delta)}d", "dias-vencida"
    if delta == 0:
        return "Hoy", "dias-warn"
    if delta <= 3:
        return f"{delta}d restantes", "dias-warn"
    return f"{delta}d restantes", "dias-ok"


def _timeline_html(pedido_id: int, estado_actual: str) -> str:
    idx_actual = ESTADOS_ORDEN.index(estado_actual) if estado_actual in ESTADOS_ORDEN else 0
    parts = []
    for i, key in enumerate(ESTADOS_ORDEN):
        label, _ = ESTADOS[key]
        if i < idx_actual:
            dot_cls, lbl_cls, icon = "done", "done", "✓"
        elif i == idx_actual:
            dot_cls, lbl_cls, icon = "active", "active", str(i + 1)
        else:
            dot_cls, lbl_cls, icon = "", "", str(i + 1)

        parts.append(f"""
        <div class="tl-step">
            <div class="tl-dot {dot_cls}"
                 onclick="cambiarEstado({pedido_id}, '{key}')"
                 title="Marcar como {label}">{icon}</div>
            <span class="tl-label {lbl_cls}">{label}</span>
        </div>""")

        if i < len(ESTADOS_ORDEN) - 1:
            line_cls = "done" if i < idx_actual else ""
            parts.append(f'<div class="tl-line {line_cls}"></div>')

    return f'<div class="timeline">{"".join(parts)}</div>'


def _build_table(pedidos: list[PedidoProduccion]) -> str:
    if not pedidos:
        return """
        <div class="prod-empty">
            <div class="empty-icon">📋</div>
            <p>No hay pedidos aún.<br>Crea el primero con el botón de arriba.</p>
        </div>"""

    rows = ""
    for p in pedidos:
        if p.imagen_path:
            img_url = f"/produccion/uploads/{os.path.basename(p.imagen_path)}"
            img_html = f'<img src="{img_url}" class="prod-thumb" onclick="openLightbox(\'{img_url}\')" title="Ver imagen">'
        else:
            img_html = '<div class="prod-thumb-placeholder">🖼</div>'

        artista_html = f'<span>{p.artista}</span>' if p.artista else ""
        timeline = _timeline_html(p.id, p.estado)

        fecha_txt = p.fecha_entrega.strftime("%d/%m/%Y") if p.fecha_entrega else "—"
        dias_txt, dias_cls = _days_remaining(p.fecha_entrega)

        rows += f"""
        <tr id="row-{p.id}">
            <td class="td-img">{img_html}</td>
            <td class="td-album">
                <strong>{p.album}</strong>
                {artista_html}
            </td>
            <td><span class="qty-badge">{p.cantidad}</span></td>
            <td>{timeline}</td>
            <td class="td-fecha">
                {fecha_txt}
                <div><span class="dias-badge {dias_cls}">{dias_txt}</span></div>
            </td>
            <td>
                <div class="td-actions">
                    <button class="btn-delete" onclick="eliminarPedido({p.id})" title="Eliminar">✕</button>
                </div>
            </td>
        </tr>"""

    return f"""
    <div class="prod-table-wrap">
        <table class="prod-table" id="prodTable">
            <thead>
                <tr>
                    <th></th>
                    <th onclick="sortTable('album')" id="th-album">Álbum / Artista <span class="sort-icon">↕</span></th>
                    <th onclick="sortTable('cantidad')" id="th-cantidad">Cant. <span class="sort-icon">↕</span></th>
                    <th>Progreso</th>
                    <th onclick="sortTable('fecha')" id="th-fecha">Entrega <span class="sort-icon">↕</span></th>
                    <th></th>
                </tr>
            </thead>
            <tbody id="prodTbody">
                {rows}
            </tbody>
        </table>
    </div>"""


def _build_modal() -> str:
    estado_opts = "".join(
        f'<option value="{k}">{v[0]}</option>' for k, v in ESTADOS.items()
    )

    # Filas de fechas por estado (se muestran/ocultan con JS según estado inicial)
    fechas_rows = ""
    for key in ESTADOS_ORDEN:
        label = ESTADOS[key][0]
        fechas_rows += f"""
        <div class="fecha-row" id="fecha-row-{key}">
            <div class="tl-dot-mini"></div>
            <label>{label}</label>
            <input type="date" name="fecha_{key}" id="fecha_{key}" class="form-input">
        </div>"""

    return f"""
    <div class="modal-overlay" id="nuevoModal">
        <div class="modal-box">
            <div class="modal-header">
                <h2>Nuevo pedido</h2>
                <button class="modal-close" onclick="closeModal()">×</button>
            </div>
            <form class="modal-form" id="nuevoForm"
                  method="POST" action="/produccion/nuevo"
                  enctype="multipart/form-data">

                <div class="form-section-title">Imagen del diseño</div>
                <div class="upload-zone" id="uploadZone">
                    <input type="file" name="imagen" id="imagenInput"
                           accept="image/*" onchange="previewImage(this)">
                    <div class="upload-icon">📁</div>
                    <div class="upload-label"><strong>Selecciona una imagen</strong> o arrastra aquí</div>
                    <div class="upload-hint">JPG, PNG, WEBP — máx. 10 MB</div>
                    <img id="uploadPreview" class="upload-preview">
                </div>

                <div class="form-section-title">Información del pedido</div>

                <div class="form-group">
                    <label for="album">Nombre del álbum *</label>
                    <input type="text" name="album" id="album" class="form-input"
                           placeholder="Ej. Formula of Love" required>
                </div>

                <div class="form-group">
                    <label for="artista">Artista</label>
                    <input type="text" name="artista" id="artista" class="form-input"
                           placeholder="Ej. TWICE" list="artistas-list" autocomplete="off">
                    <datalist id="artistas-list"></datalist>
                </div>

                <div class="form-row">
                    <div class="form-group">
                        <label for="cantidad">Cantidad *</label>
                        <input type="number" name="cantidad" id="cantidad"
                               class="form-input" min="1" placeholder="1" required>
                    </div>
                    <div class="form-group">
                        <label for="estado">Estado inicial</label>
                        <select name="estado" id="estadoSelect" class="form-select"
                                onchange="updateFechasVisibility()">
                            {estado_opts}
                        </select>
                    </div>
                </div>

                <div class="form-section-title">Fechas de objetivos</div>
                <div class="fechas-grid">
                    {fechas_rows}
                </div>

                <div class="form-group">
                    <label for="fecha_entrega">Fecha de entrega final *</label>
                    <input type="date" name="fecha_entrega" id="fecha_entrega"
                           class="form-input" required>
                </div>

                <div class="form-section-title">Notas y recordatorios</div>
                <div class="form-group">
                    <label for="recordatorios">Recordatorios adicionales</label>
                    <textarea name="recordatorios" id="recordatorios" class="form-textarea"
                              rows="2" placeholder="Ej. Llamar al cliente el viernes, revisar material..."></textarea>
                    <span class="form-hint">Se usarán para notificaciones por Telegram (próximamente)</span>
                </div>

                <div class="form-group">
                    <label for="notas">Notas internas</label>
                    <textarea name="notas" id="notas" class="form-textarea"
                              rows="2" placeholder="Detalles del pedido..."></textarea>
                </div>

                <div class="form-actions">
                    <button type="button" class="btn-cancel" onclick="closeModal()">Cancelar</button>
                    <button type="submit" class="btn-submit">Crear pedido</button>
                </div>
            </form>
        </div>
    </div>

    <div class="lightbox" id="lightbox" onclick="closeLightbox()">
        <button class="lightbox-close" onclick="closeLightbox()">×</button>
        <img id="lightboxImg" src="">
    </div>"""


def _build_js() -> str:
    estados_orden_js = str(ESTADOS_ORDEN)  # e.g. ['diseno', 'impresion', 'limpiado', 'clavado']
    return f"""
    <script>
    const ESTADOS_ORDEN = {estados_orden_js};

    // ── Modal ──
    function openModal() {{
        document.getElementById('nuevoModal').classList.add('open');
        loadArtistas();
        updateFechasVisibility();
    }}
    function closeModal() {{
        document.getElementById('nuevoModal').classList.remove('open');
    }}
    document.getElementById('nuevoModal').addEventListener('click', function(e) {{
        if (e.target === this) closeModal();
    }});
    document.addEventListener('keydown', e => {{
        if (e.key === 'Escape') {{ closeModal(); closeLightbox(); }}
    }});

    // ── Autofill artistas ──
    async function loadArtistas() {{
        try {{
            const res = await fetch('/produccion/api/artistas');
            const data = await res.json();
            const dl = document.getElementById('artistas-list');
            dl.innerHTML = data.map(a => `<option value="${{a}}"></option>`).join('');
        }} catch(_) {{}}
    }}

    // ── Fechas dinámicas según estado inicial ──
    function updateFechasVisibility() {{
        const sel = document.getElementById('estadoSelect');
        if (!sel) return;
        const idxInicial = ESTADOS_ORDEN.indexOf(sel.value);
        ESTADOS_ORDEN.forEach((key, i) => {{
            const row = document.getElementById('fecha-row-' + key);
            if (!row) return;
            if (i < idxInicial) {{
                row.classList.add('hidden');
                row.querySelector('input').value = '';
            }} else {{
                row.classList.remove('hidden');
            }}
        }});
    }}

    // ── Upload preview ──
    function previewImage(input) {{
        const preview = document.getElementById('uploadPreview');
        if (input.files && input.files[0]) {{
            const reader = new FileReader();
            reader.onload = e => {{ preview.src = e.target.result; preview.style.display = 'block'; }};
            reader.readAsDataURL(input.files[0]);
        }}
    }}
    const zone = document.getElementById('uploadZone');
    if (zone) {{
        zone.addEventListener('dragover', () => zone.classList.add('drag-over'));
        zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
        zone.addEventListener('drop', () => zone.classList.remove('drag-over'));
    }}

    // ── Lightbox ──
    function openLightbox(src) {{
        document.getElementById('lightboxImg').src = src;
        document.getElementById('lightbox').classList.add('open');
    }}
    function closeLightbox() {{
        document.getElementById('lightbox').classList.remove('open');
    }}

    // ── Cambiar estado (click en timeline) ──
    async function cambiarEstado(id, nuevoEstado) {{
        const res = await fetch(`/produccion/${{id}}/status`, {{
            method: 'POST',
            headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify({{ estado: nuevoEstado }})
        }});
        if (res.ok) location.reload();
        else alert('Error al actualizar el estado');
    }}

    // ── Eliminar ──
    async function eliminarPedido(id) {{
        if (!confirm('¿Eliminar este pedido?')) return;
        const res = await fetch(`/produccion/${{id}}`, {{ method: 'DELETE' }});
        if (res.ok) {{
            const row = document.getElementById('row-' + id);
            if (row) row.remove();
        }} else alert('Error al eliminar');
    }}

    // ── Ordenar tabla ──
    let sortState = {{ col: null, asc: true }};
    function sortTable(col) {{
        const tbody = document.getElementById('prodTbody');
        if (!tbody) return;
        const rows = Array.from(tbody.querySelectorAll('tr'));
        sortState.asc = sortState.col === col ? !sortState.asc : true;
        sortState.col = col;

        document.querySelectorAll('.prod-table thead th').forEach(th => th.classList.remove('sorted'));
        const thMap = {{ album: 'th-album', cantidad: 'th-cantidad', fecha: 'th-fecha' }};
        const activeTh = document.getElementById(thMap[col]);
        if (activeTh) {{
            activeTh.classList.add('sorted');
            activeTh.querySelector('.sort-icon').textContent = sortState.asc ? '↑' : '↓';
        }}

        const colIndex = {{ album: 1, cantidad: 2, fecha: 4 }};
        const idx = colIndex[col];
        rows.sort((a, b) => {{
            const aV = a.cells[idx]?.textContent.trim() ?? '';
            const bV = b.cells[idx]?.textContent.trim() ?? '';
            if (col === 'cantidad') return sortState.asc ? parseInt(aV)-parseInt(bV) : parseInt(bV)-parseInt(aV);
            return sortState.asc ? aV.localeCompare(bV,'es') : bV.localeCompare(aV,'es');
        }});
        rows.forEach(r => tbody.appendChild(r));
    }}
    </script>"""


def _page(pedidos: list[PedidoProduccion], sort: str, order: str) -> str:
    table_html = _build_table(pedidos)
    modal_html = _build_modal()
    js_html = _build_js()

    sort_opts = [
        ("fecha_creacion", "Más recientes"),
        ("fecha_entrega",  "Fecha de entrega"),
        ("cantidad",       "Cantidad"),
        ("album",          "Álbum"),
    ]
    s_opts = "".join(
        f'<option value="{v}" {"selected" if v==sort else ""}>{l}</option>'
        for v, l in sort_opts
    )
    o_opts = (
        f'<option value="desc" {"selected" if order=="desc" else ""}>Descendente</option>'
        f'<option value="asc"  {"selected" if order=="asc"  else ""}>Ascendente</option>'
    )

    content = f"""
    <style>{PRODUCCION_CSS}</style>

    <div class="prod-header">
        <h1>Pedidos</h1>
        <button class="btn" onclick="openModal()">+ Nuevo pedido</button>
    </div>

    <div class="prod-toolbar">
        <select class="sort-select" id="sortBy" onchange="applySort()">{s_opts}</select>
        <select class="sort-select" id="sortOrder" onchange="applySort()">{o_opts}</select>
        <div class="clientes-placeholder">
            <span>👥</span> Agregar clientes
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
    return base_layout("Pedidos", content, active="produccion")


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
async def produccion_index(sort: str = "fecha_creacion", order: str = "desc"):
    session_factory = get_session_factory()
    async with session_factory() as session:
        col_map = {
            "fecha_creacion": PedidoProduccion.fecha_creacion,
            "fecha_entrega":  PedidoProduccion.fecha_entrega,
            "cantidad":       PedidoProduccion.cantidad,
            "album":          PedidoProduccion.album,
        }
        col = col_map.get(sort, PedidoProduccion.fecha_creacion)
        direction = col.desc() if order == "desc" else col.asc()
        result = await session.execute(select(PedidoProduccion).order_by(direction))
        pedidos = result.scalars().all()
    return _page(list(pedidos), sort, order)


@router.get("/api/artistas")
async def get_artistas():
    session_factory = get_session_factory()
    async with session_factory() as session:
        result = await session.execute(select(Artista.nombre).order_by(Artista.nombre))
        nombres = result.scalars().all()
    return nombres


@router.post("/nuevo")
async def crear_pedido(
    album: str = Form(...),
    cantidad: int = Form(...),
    estado: str = Form("diseno"),
    artista: str = Form(""),
    fecha_entrega: str = Form(...),
    fecha_diseno: str = Form(""),
    fecha_impresion: str = Form(""),
    fecha_limpiado: str = Form(""),
    fecha_clavado: str = Form(""),
    recordatorios: str = Form(""),
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

    def parse_date(s: str) -> datetime | None:
        if not s:
            return None
        try:
            return datetime.fromisoformat(s)
        except ValueError:
            return None

    estado_clean = estado if estado in ESTADOS else "diseno"

    pedido = PedidoProduccion(
        album=album.strip(),
        artista=artista.strip() or None,
        cantidad=cantidad,
        estado=estado_clean,
        imagen_path=imagen_path,
        fecha_entrega=parse_date(fecha_entrega),
        fecha_diseno=parse_date(fecha_diseno),
        fecha_impresion=parse_date(fecha_impresion),
        fecha_limpiado=parse_date(fecha_limpiado),
        fecha_clavado=parse_date(fecha_clavado),
        recordatorios=recordatorios.strip() or None,
        notas=notas.strip() or None,
    )

    session_factory = get_session_factory()
    async with session_factory() as session:
        session.add(pedido)
        # Guardar artista en tabla de artistas si no existe
        if artista.strip():
            existing = await session.execute(
                select(Artista).where(Artista.nombre == artista.strip())
            )
            if not existing.scalar_one_or_none():
                session.add(Artista(nombre=artista.strip()))
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
        if pedido.imagen_path and os.path.exists(pedido.imagen_path):
            os.remove(pedido.imagen_path)
        await session.delete(pedido)
        await session.commit()
    return JSONResponse({"ok": True})


@router.get("/uploads/{filename}")
async def serve_upload(filename: str):
    safe_name = os.path.basename(filename)
    path = os.path.join(UPLOADS_DIR, safe_name)
    if not os.path.exists(path):
        return JSONResponse(status_code=404, content={"detail": "Imagen no encontrada"})
    return FileResponse(path)
