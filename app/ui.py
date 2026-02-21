"""Componentes de UI compartidos — layout base, nav, estilos, modal."""


# ── Design tokens & global CSS ──────────────────────────────────────────────

GLOBAL_CSS = """
:root {
    /* Neutrals */
    --bg:            #f0f2f5;
    --surface:       #ffffff;
    --surface-2:     #f8fafc;
    --surface-hover: #f1f5f9;

    /* Brand */
    --primary:       #1a2332;
    --primary-light: #263348;
    --accent:        #2d72d9;
    --accent-hover:  #2563c8;
    --accent-soft:   #eff6ff;

    /* Text */
    --text:          #111827;
    --text-secondary:#4b5563;
    --text-muted:    #9ca3af;

    /* Borders */
    --border:        #e5e7eb;
    --border-strong: #d1d5db;

    /* Status */
    --success:       #059669;
    --success-bg:    #ecfdf5;
    --success-text:  #065f46;
    --warning:       #d97706;
    --warning-bg:    #fffbeb;
    --warning-text:  #92400e;
    --danger:        #dc2626;
    --danger-bg:     #fef2f2;
    --danger-text:   #991b1b;
    --info:          #0891b2;
    --info-bg:       #ecfeff;
    --info-text:     #155e75;

    /* Shape */
    --radius:        10px;
    --radius-sm:     6px;
    --radius-lg:     16px;

    /* Shadows */
    --shadow-sm:  0 1px 2px rgba(0,0,0,0.05);
    --shadow:     0 1px 3px rgba(0,0,0,0.07), 0 1px 2px rgba(0,0,0,0.05);
    --shadow-md:  0 4px 8px rgba(0,0,0,0.06), 0 2px 4px rgba(0,0,0,0.04);
    --shadow-lg:  0 10px 24px rgba(0,0,0,0.09), 0 4px 8px rgba(0,0,0,0.05);
    --shadow-xl:  0 20px 48px rgba(0,0,0,0.13);

    /* Transitions */
    --transition: 0.15s ease;
}

*, *::before, *::after { margin: 0; padding: 0; box-sizing: border-box; }

html { scroll-behavior: smooth; }

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Inter', Roboto, sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.55;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}

/* ── NAVBAR ── */
.navbar {
    background: var(--primary);
    padding: 0 28px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    height: 62px;
    position: sticky;
    top: 0;
    z-index: 200;
    box-shadow: 0 1px 0 rgba(255,255,255,0.05), 0 2px 8px rgba(0,0,0,0.18);
}

.navbar .brand {
    color: #fff;
    font-size: 16px;
    font-weight: 700;
    letter-spacing: -0.3px;
    text-decoration: none;
    display: flex;
    align-items: center;
    gap: 10px;
}

.brand-logo {
    width: 32px;
    height: 32px;
    background: linear-gradient(135deg, #ffe600 0%, #f5a623 100%);
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 16px;
    flex-shrink: 0;
}

.brand-name {
    color: #fff;
    font-weight: 700;
    font-size: 15px;
}

.brand-tag {
    background: rgba(255,255,255,0.12);
    color: rgba(255,255,255,0.7);
    font-size: 10px;
    padding: 2px 7px;
    border-radius: 4px;
    font-weight: 500;
    letter-spacing: 0.5px;
    text-transform: uppercase;
}

.nav-links {
    display: flex;
    gap: 2px;
}

.nav-links a {
    color: rgba(255,255,255,0.6);
    text-decoration: none;
    padding: 7px 14px;
    border-radius: var(--radius-sm);
    font-size: 13.5px;
    font-weight: 500;
    transition: all var(--transition);
    letter-spacing: 0.1px;
}

.nav-links a:hover {
    color: #fff;
    background: rgba(255,255,255,0.09);
}

.nav-links a.active {
    color: #fff;
    background: rgba(255,255,255,0.13);
}

/* ── MOBILE NAV ── */
.mobile-nav {
    display: none;
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    background: var(--surface);
    border-top: 1px solid var(--border);
    padding: 6px 0;
    padding-bottom: max(6px, env(safe-area-inset-bottom));
    z-index: 200;
}

.mobile-nav .nav-links {
    justify-content: center;
    gap: 0;
}

.mobile-nav .nav-links a {
    color: var(--text-muted);
    flex: 1;
    text-align: center;
    font-size: 11px;
    padding: 8px 4px;
    border-radius: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 3px;
}

.mobile-nav .nav-links a.active {
    color: var(--accent);
    background: transparent;
    font-weight: 600;
}

/* ── LAYOUT ── */
.container {
    max-width: 1240px;
    margin: 0 auto;
    padding: 28px 24px;
}

.page-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 12px;
    margin-bottom: 24px;
}

.page-title {
    font-size: 22px;
    font-weight: 700;
    color: var(--text);
    letter-spacing: -0.4px;
    line-height: 1.2;
}

.page-subtitle {
    font-size: 13.5px;
    color: var(--text-secondary);
    margin-top: 3px;
}

/* ── STAT CARDS ── */
.stats {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
    gap: 16px;
    margin-bottom: 24px;
}

.stat-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 20px 22px;
    box-shadow: var(--shadow);
    position: relative;
    overflow: hidden;
}

.stat-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 3px;
    height: 100%;
    background: var(--border-strong);
    border-radius: 3px 0 0 3px;
}

.stat-card.accent::before  { background: var(--accent); }
.stat-card.success::before { background: var(--success); }
.stat-card.warning::before { background: var(--warning); }
.stat-card.danger::before  { background: var(--danger); }

.stat-label {
    font-size: 12px;
    color: var(--text-secondary);
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    margin-bottom: 10px;
}

.stat-value {
    font-size: 30px;
    font-weight: 800;
    color: var(--text);
    letter-spacing: -1.5px;
    line-height: 1;
}

.stat-card.danger  .stat-value { color: var(--danger); }
.stat-card.warning .stat-value { color: var(--warning); }
.stat-card.success .stat-value { color: var(--success); }
.stat-card.accent  .stat-value { color: var(--accent); }

.stat-detail {
    font-size: 12px;
    color: var(--text-muted);
    margin-top: 6px;
}

/* ── TABLE ── */
.table-wrapper {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    box-shadow: var(--shadow);
    overflow: hidden;
    margin-bottom: 20px;
}

.table-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px 22px;
    border-bottom: 1px solid var(--border);
    background: var(--surface-2);
}

.table-header h2 {
    font-size: 15px;
    font-weight: 600;
    color: var(--text);
}

table { width: 100%; border-collapse: collapse; }

th {
    padding: 11px 22px;
    text-align: left;
    font-size: 11.5px;
    font-weight: 600;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.6px;
    border-bottom: 1px solid var(--border);
    background: var(--surface-2);
    white-space: nowrap;
}

td {
    padding: 14px 22px;
    font-size: 13.5px;
    border-bottom: 1px solid var(--border);
    vertical-align: top;
}

tr:last-child td { border-bottom: none; }

tbody tr:hover td { background: var(--surface-hover); cursor: pointer; }

/* ── BUTTONS ── */
.btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 8px 16px;
    border-radius: var(--radius-sm);
    font-size: 13px;
    font-weight: 500;
    text-decoration: none;
    border: 1px solid var(--border);
    background: var(--surface);
    color: var(--text);
    cursor: pointer;
    transition: all var(--transition);
    white-space: nowrap;
    letter-spacing: 0.1px;
}

.btn:hover {
    background: var(--surface-hover);
    border-color: var(--border-strong);
    box-shadow: var(--shadow-sm);
}

.btn-primary {
    background: var(--accent);
    color: #fff;
    border-color: var(--accent);
}

.btn-primary:hover {
    background: var(--accent-hover);
    border-color: var(--accent-hover);
    box-shadow: 0 2px 6px rgba(45,114,217,0.3);
}

.btn-sm {
    padding: 5px 12px;
    font-size: 12px;
}

.btn-danger {
    background: var(--danger-bg);
    color: var(--danger-text);
    border-color: #fca5a5;
}

.btn-danger:hover {
    background: #fee2e2;
}

/* ── BADGES ── */
.badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 11.5px;
    font-weight: 600;
    letter-spacing: 0.2px;
    white-space: nowrap;
}

.badge-success { background: var(--success-bg); color: var(--success-text); }
.badge-warning { background: var(--warning-bg); color: var(--warning-text); }
.badge-danger  { background: var(--danger-bg);  color: var(--danger-text); }
.badge-neutral { background: var(--surface-2);  color: var(--text-secondary); border: 1px solid var(--border); }
.badge-accent  { background: var(--accent-soft); color: #1e40af; }
.badge-info    { background: var(--info-bg); color: var(--info-text); }

/* Pulse animation for urgent/delayed */
.badge.pulse {
    animation: badge-pulse 2.2s ease-in-out infinite;
}
@keyframes badge-pulse {
    0%, 100% { opacity: 1; box-shadow: 0 0 0 0 rgba(220,38,38,0); }
    50%       { opacity: 0.82; box-shadow: 0 0 0 3px rgba(220,38,38,0.12); }
}

/* ── EMPTY STATE ── */
.empty-state {
    text-align: center;
    padding: 64px 24px;
    color: var(--text-muted);
}

.empty-state .icon {
    font-size: 44px;
    margin-bottom: 14px;
    opacity: 0.35;
    display: block;
}

.empty-state p {
    font-size: 15px;
    color: var(--text-secondary);
}

/* ── ORDER CARDS (dashboard list) ── */
.order-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 16px 18px;
    margin-bottom: 10px;
    box-shadow: var(--shadow-sm);
    cursor: pointer;
    transition: box-shadow var(--transition), transform var(--transition);
}

.order-card:hover {
    box-shadow: var(--shadow-md);
    transform: translateY(-1px);
}

.order-card-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 10px;
    gap: 8px;
}

.order-card-header .order-id {
    font-weight: 700;
    font-size: 14.5px;
}

.order-card-row {
    display: flex;
    justify-content: space-between;
    font-size: 13px;
    padding: 3px 0;
}

.order-card-row .label {
    color: var(--text-secondary);
}

.order-card-products {
    font-size: 13px;
    padding: 8px 0;
    border-top: 1px solid var(--border);
    border-bottom: 1px solid var(--border);
    margin: 6px 0;
    color: var(--text-secondary);
}

/* ── SPINNER ── */
.loading {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 48px;
    color: var(--text-muted);
    gap: 10px;
}

.spinner {
    width: 20px;
    height: 20px;
    border: 2px solid var(--border);
    border-top-color: var(--accent);
    border-radius: 50%;
    animation: spin 0.65s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

/* ── ERROR BANNER ── */
.error-banner {
    background: var(--danger-bg);
    border: 1px solid #fca5a5;
    border-radius: var(--radius);
    padding: 16px 20px;
    margin-bottom: 24px;
    display: flex;
    align-items: flex-start;
    gap: 12px;
}

.error-banner strong { color: var(--danger-text); font-size: 14px; }
.error-banner p { color: #b91c1c; font-size: 13px; margin-top: 3px; }

/* ── PEDIDO CARDS (ventas page) ── */
.section {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    box-shadow: var(--shadow);
    overflow: hidden;
    margin-bottom: 20px;
}

.section-header {
    padding: 14px 22px;
    border-bottom: 1px solid var(--border);
    background: var(--surface-2);
    display: flex;
    align-items: center;
    gap: 8px;
}

.section-header h2 {
    font-size: 15px;
    font-weight: 600;
    color: var(--text);
}

.section-count {
    font-weight: 400;
    color: var(--text-muted);
    font-size: 13px;
}

.pedido-card {
    border-bottom: 1px solid var(--border);
    transition: background var(--transition);
    cursor: pointer;
}

.pedido-card:last-child { border-bottom: none; }

.pedido-card:hover .pedido-header { background: var(--surface-hover); }

.pedido-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 13px 22px;
    flex-wrap: wrap;
    gap: 8px;
    transition: background var(--transition);
}

.pedido-title {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
    font-size: 14.5px;
    font-weight: 600;
}

.pedido-title .buyer {
    color: var(--text-secondary);
    font-weight: 400;
    font-size: 13px;
}

.pedido-badges {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
    align-items: center;
}

.pedido-body {
    padding: 14px 22px 18px;
    display: grid;
    grid-template-columns: 1fr auto 116px;
    gap: 24px;
    align-items: start;
}

.pedido-items { font-size: 13.5px; }

.product-line {
    padding: 4px 0;
    display: flex;
    align-items: baseline;
    gap: 6px;
    flex-wrap: wrap;
}

.product-line .qty {
    font-weight: 700;
    color: var(--accent);
    font-size: 12.5px;
    background: var(--accent-soft);
    padding: 1px 7px;
    border-radius: 10px;
}

.product-line .sku {
    color: var(--text-muted);
    font-size: 11px;
    font-family: 'SF Mono', 'Fira Code', monospace;
}

.pedido-thumb-wrap {
    display: flex;
    align-items: flex-start;
    justify-content: center;
    padding-top: 2px;
}

.pedido-thumb {
    width: 104px;
    height: 104px;
    object-fit: contain;
    border-radius: 10px;
    border: 1px solid var(--border);
    background: #fff;
    box-shadow: var(--shadow-sm);
}

.pedido-thumb-empty {
    width: 104px;
    height: 104px;
    border-radius: 10px;
    border: 2px dashed var(--border);
    background: var(--surface-2);
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--text-muted);
    font-size: 28px;
    opacity: 0.5;
}

.btn-label {
    font-size: 12px;
    padding: 5px 12px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    color: var(--text);
    text-decoration: none;
    white-space: nowrap;
    display: inline-flex;
    align-items: center;
    gap: 5px;
    transition: all var(--transition);
}

.btn-label:hover {
    background: var(--accent-soft);
    border-color: var(--accent);
    color: var(--accent);
}

.pedido-meta {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px 20px;
    font-size: 13px;
    align-content: start;
}

.meta-item { display: flex; flex-direction: column; gap: 2px; }

.meta-label {
    color: var(--text-muted);
    font-size: 10.5px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    font-weight: 600;
}

.meta-value {
    color: var(--text);
    font-size: 13px;
}

/* ── ORDER DETAIL MODAL ── */
.modal-backdrop {
    display: none;
    position: fixed;
    inset: 0;
    background: rgba(10,14,23,0.55);
    z-index: 500;
    backdrop-filter: blur(3px);
    -webkit-backdrop-filter: blur(3px);
    overflow-y: auto;
    padding: 24px 16px;
}

.modal-backdrop.open { display: flex; align-items: flex-start; justify-content: center; }

.modal {
    background: var(--surface);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-xl);
    width: 100%;
    max-width: 800px;
    overflow: hidden;
    animation: modal-in 0.22s cubic-bezier(0.34,1.26,0.64,1);
    margin: auto;
}

@keyframes modal-in {
    from { opacity: 0; transform: scale(0.96) translateY(8px); }
    to   { opacity: 1; transform: scale(1) translateY(0); }
}

.modal-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 20px 26px;
    border-bottom: 1px solid var(--border);
    background: var(--primary);
    color: #fff;
}

.modal-header-left { display: flex; flex-direction: column; gap: 4px; }

.modal-order-id {
    font-size: 18px;
    font-weight: 700;
    letter-spacing: -0.3px;
}

.modal-date {
    font-size: 12.5px;
    color: rgba(255,255,255,0.55);
}

.modal-close {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    background: rgba(255,255,255,0.1);
    border: none;
    color: #fff;
    font-size: 20px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: background var(--transition);
    flex-shrink: 0;
    line-height: 1;
}

.modal-close:hover { background: rgba(255,255,255,0.18); }

.modal-hero {
    display: grid;
    grid-template-columns: 200px 1fr;
    gap: 0;
}

.modal-photo-panel {
    background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 32px 20px;
    border-right: 1px solid var(--border);
    min-height: 200px;
}

.modal-photo {
    max-width: 160px;
    max-height: 160px;
    width: 100%;
    height: auto;
    object-fit: contain;
    border-radius: 12px;
    box-shadow: var(--shadow-md);
}

.modal-photo-placeholder {
    width: 120px;
    height: 120px;
    background: var(--border);
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 40px;
    opacity: 0.4;
}

.modal-info-panel {
    padding: 24px 28px;
}

.modal-product-title {
    font-size: 17px;
    font-weight: 700;
    color: var(--text);
    line-height: 1.35;
    margin-bottom: 14px;
}

.modal-status-row {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    margin-bottom: 18px;
    align-items: center;
}

.modal-meta-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 14px 28px;
}

.modal-meta-item { display: flex; flex-direction: column; gap: 3px; }

.modal-meta-label {
    font-size: 11px;
    color: var(--text-muted);
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.6px;
}

.modal-meta-value {
    font-size: 14px;
    color: var(--text);
    font-weight: 500;
}

.modal-meta-value.highlight {
    color: var(--accent);
    font-weight: 700;
}

.modal-meta-value.danger {
    color: var(--danger);
    font-weight: 700;
}

.modal-divider {
    border: none;
    border-top: 1px solid var(--border);
    margin: 0;
}

.modal-items-section {
    padding: 20px 28px;
}

.modal-section-title {
    font-size: 13px;
    font-weight: 600;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.6px;
    margin-bottom: 14px;
}

.modal-item-row {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 12px 0;
    border-bottom: 1px solid var(--border);
}

.modal-item-row:last-child { border-bottom: none; }

.modal-item-thumb {
    width: 56px;
    height: 56px;
    object-fit: contain;
    border-radius: 8px;
    border: 1px solid var(--border);
    background: #fff;
    flex-shrink: 0;
}

.modal-item-thumb-empty {
    width: 56px;
    height: 56px;
    border-radius: 8px;
    border: 1px dashed var(--border);
    background: var(--surface-2);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 22px;
    flex-shrink: 0;
    opacity: 0.5;
}

.modal-item-info { flex: 1; min-width: 0; }

.modal-item-title {
    font-size: 13.5px;
    font-weight: 500;
    color: var(--text);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.modal-item-sku {
    font-size: 11.5px;
    color: var(--text-muted);
    font-family: 'SF Mono','Fira Code',monospace;
    margin-top: 2px;
}

.modal-item-right {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 4px;
    flex-shrink: 0;
}

.modal-item-qty {
    font-weight: 700;
    font-size: 14px;
    color: var(--accent);
    background: var(--accent-soft);
    padding: 2px 10px;
    border-radius: 12px;
}

.modal-item-price {
    font-size: 12.5px;
    color: var(--text-secondary);
}

.modal-footer {
    padding: 18px 28px;
    border-top: 1px solid var(--border);
    background: var(--surface-2);
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
    flex-wrap: wrap;
}

.modal-total {
    display: flex;
    flex-direction: column;
    gap: 2px;
}

.modal-total-label {
    font-size: 11.5px;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    font-weight: 600;
}

.modal-total-amount {
    font-size: 22px;
    font-weight: 800;
    color: var(--text);
    letter-spacing: -0.5px;
}

.modal-footer-actions {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
}

/* ── LOADING SKELETON ── */
.modal-loading {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 80px 40px;
    gap: 16px;
    color: var(--text-muted);
}

.modal-loading .spinner { width: 28px; height: 28px; border-width: 3px; }
.modal-loading p { font-size: 14px; }

/* ── RESPONSIVE ── */
@media (max-width: 768px) {
    .navbar { padding: 0 16px; }
    .navbar .nav-links { display: none; }
    .mobile-nav { display: block; }
    body { padding-bottom: 68px; }

    .container { padding: 16px 14px; }
    .page-title { font-size: 19px; }
    .stats { grid-template-columns: repeat(2, 1fr); gap: 10px; }
    .stat-card { padding: 15px 16px; }
    .stat-value { font-size: 26px; }

    .pedido-header { padding: 11px 16px; flex-direction: column; align-items: flex-start; }
    .pedido-body {
        padding: 12px 16px 16px;
        grid-template-columns: 1fr auto;
        grid-template-rows: auto auto;
        gap: 14px;
    }
    .pedido-thumb-wrap {
        grid-column: 2;
        grid-row: 1 / 3;
    }
    .pedido-thumb, .pedido-thumb-empty { width: 76px; height: 76px; }
    .pedido-meta { grid-template-columns: 1fr 1fr; gap: 10px; }
    .section-header { padding: 12px 16px; }

    .modal-hero { grid-template-columns: 1fr; }
    .modal-photo-panel { border-right: none; border-bottom: 1px solid var(--border); padding: 24px; min-height: 160px; }
    .modal-info-panel { padding: 18px 20px; }
    .modal-meta-grid { grid-template-columns: 1fr 1fr; }
    .modal-items-section { padding: 16px 20px; }
    .modal-footer { padding: 16px 20px; }
    .modal-header { padding: 16px 20px; }
    .modal-order-id { font-size: 16px; }
}

@media (max-width: 480px) {
    .stats { grid-template-columns: repeat(2, 1fr); gap: 8px; }
    .stat-value { font-size: 23px; }
    .modal-meta-grid { grid-template-columns: 1fr; }
    .modal-footer { flex-direction: column; align-items: flex-start; }
}
"""


# ── JavaScript for modal ─────────────────────────────────────────────────────

MODAL_JS = """
<script>
(function() {
    const backdrop = document.getElementById('order-modal-backdrop');
    const modalBody = document.getElementById('modal-body');

    function openModal(orderId) {
        backdrop.classList.add('open');
        document.body.style.overflow = 'hidden';
        renderLoading();
        fetchOrder(orderId);
    }

    function closeModal() {
        backdrop.classList.remove('open');
        document.body.style.overflow = '';
        modalBody.innerHTML = '';
    }

    function renderLoading() {
        modalBody.innerHTML = `
            <div class="modal-loading">
                <div class="spinner"></div>
                <p>Cargando detalle del pedido…</p>
            </div>`;
    }

    function fmtDate(str) {
        if (!str) return '—';
        try {
            const d = new Date(str);
            return d.toLocaleString('es-MX', {
                day:'2-digit', month:'short', year:'numeric',
                hour:'2-digit', minute:'2-digit'
            });
        } catch(e) { return str; }
    }

    function fmtMoney(amount, currency) {
        if (amount == null) return '—';
        return new Intl.NumberFormat('es-MX', {
            style: 'currency', currency: currency || 'MXN', minimumFractionDigits: 2
        }).format(amount);
    }

    function categoryColor(cat) {
        const map = {
            delayed: '#dc2626',
            ready:   '#2d72d9',
            shipped: '#059669',
            pending: '#d97706'
        };
        return map[cat] || '#6b7280';
    }

    function buildLabelBtn(o) {
        const okSub = ['ready_to_print','printed','handling_time_over'];
        if (o.shipment_id && okSub.includes(o.shipping_substatus_raw)) {
            return `<a href="https://www.mercadolibre.com.mx/envios/${o.shipment_id}/ver_etiqueta"
                      target="_blank" class="btn btn-primary">
                      Imprimir etiqueta
                    </a>`;
        }
        return '';
    }

    function buildModal(o) {
        const photo = (o.items && o.items.length > 0 && o.items[0].thumbnail)
            ? `<img src="${o.items[0].thumbnail}" class="modal-photo" alt="Foto del producto">`
            : `<div class="modal-photo-placeholder">📦</div>`;

        const mainTitle = (o.items && o.items.length > 0)
            ? o.items[0].title
            : 'Pedido sin detalle';

        const deadlineClass = (o.category === 'delayed') ? ' danger' : '';
        const deadlineVal = o.deadline_str ? fmtDate(o.deadline_str) : '—';
        const deliveryVal = o.delivery_str ? fmtDate(o.delivery_str) : '—';

        const itemsHtml = (o.items || []).map(item => {
            const thumb = item.thumbnail
                ? `<img src="${item.thumbnail}" class="modal-item-thumb" alt="">`
                : `<div class="modal-item-thumb-empty">📦</div>`;
            const skuHtml = item.sku
                ? `<div class="modal-item-sku">SKU: ${item.sku}</div>`
                : '';
            const price = item.unit_price != null
                ? `<div class="modal-item-price">${fmtMoney(item.unit_price, o.currency)} c/u</div>`
                : '';
            return `
                <div class="modal-item-row">
                    ${thumb}
                    <div class="modal-item-info">
                        <div class="modal-item-title">${item.title}</div>
                        ${skuHtml}
                    </div>
                    <div class="modal-item-right">
                        <span class="modal-item-qty">x${item.qty}</span>
                        ${price}
                    </div>
                </div>`;
        }).join('');

        const labelBtn = buildLabelBtn(o);

        return `
        <div class="modal">
            <div class="modal-header" style="border-bottom-color: ${categoryColor(o.category)}30;">
                <div class="modal-header-left">
                    <div class="modal-order-id">Pedido #${o.order_id}</div>
                    <div class="modal-date">${fmtDate(o.date_created)}</div>
                </div>
                <button class="modal-close" onclick="closeOrderModal()" aria-label="Cerrar">&times;</button>
            </div>

            <div class="modal-hero">
                <div class="modal-photo-panel">${photo}</div>
                <div class="modal-info-panel">
                    <div class="modal-product-title">${mainTitle}</div>
                    <div class="modal-status-row">
                        <span class="badge ${o.status_cls}">${o.status_label}</span>
                        <span class="badge ${o.tiempo_cls}">${o.tiempo_text}</span>
                    </div>
                    <div class="modal-meta-grid">
                        <div class="modal-meta-item">
                            <span class="modal-meta-label">Comprador</span>
                            <span class="modal-meta-value">${o.buyer || '—'}</span>
                        </div>
                        <div class="modal-meta-item">
                            <span class="modal-meta-label">Logística</span>
                            <span class="modal-meta-value">${o.logistic || '—'}</span>
                        </div>
                        <div class="modal-meta-item">
                            <span class="modal-meta-label">Despachar antes de</span>
                            <span class="modal-meta-value${deadlineClass}">${deadlineVal}</span>
                        </div>
                        <div class="modal-meta-item">
                            <span class="modal-meta-label">Entrega estimada</span>
                            <span class="modal-meta-value">${deliveryVal}</span>
                        </div>
                    </div>
                </div>
            </div>

            <hr class="modal-divider">

            <div class="modal-items-section">
                <div class="modal-section-title">Artículos del pedido</div>
                ${itemsHtml || '<p style="color:var(--text-muted);font-size:13px;">Sin artículos disponibles.</p>'}
            </div>

            <div class="modal-footer">
                <div class="modal-total">
                    <span class="modal-total-label">Total del pedido</span>
                    <span class="modal-total-amount">${fmtMoney(o.total, o.currency)}</span>
                </div>
                <div class="modal-footer-actions">
                    ${labelBtn}
                    <button class="btn" onclick="closeOrderModal()">Cerrar</button>
                </div>
            </div>
        </div>`;
    }

    async function fetchOrder(orderId) {
        try {
            const resp = await fetch('/ventas/api/orden/' + orderId);
            if (!resp.ok) throw new Error('HTTP ' + resp.status);
            const data = await resp.json();
            if (data.error) throw new Error(data.error);
            modalBody.innerHTML = buildModal(data);
        } catch(err) {
            modalBody.innerHTML = `
                <div class="modal">
                    <div class="modal-header">
                        <div class="modal-header-left">
                            <div class="modal-order-id">Error</div>
                        </div>
                        <button class="modal-close" onclick="closeOrderModal()">&times;</button>
                    </div>
                    <div style="padding:40px;text-align:center;color:var(--danger);">
                        <p style="font-size:14px;">No se pudo cargar el detalle del pedido.</p>
                        <p style="font-size:12px;color:var(--text-muted);margin-top:8px;">${err.message}</p>
                    </div>
                </div>`;
        }
    }

    // Close on backdrop click
    backdrop.addEventListener('click', function(e) {
        if (e.target === backdrop) closeModal();
    });

    // Close on ESC
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') closeModal();
    });

    // Expose globally
    window.openOrderModal = openModal;
    window.closeOrderModal = closeModal;
})();
</script>
"""

MODAL_HTML = """
<div id="order-modal-backdrop" class="modal-backdrop" role="dialog" aria-modal="true" aria-label="Detalle de pedido">
    <div id="modal-body"></div>
</div>
"""


def base_layout(title: str, content: str, active: str = "") -> str:
    """Genera el HTML completo con layout, nav, estilos y modal de detalle."""
    nav_items = [
        ("Dashboard", "/", "dashboard"),
        ("Ventas", "/ventas/", "ventas"),
        ("Notificaciones", "/notificaciones/", "notificaciones"),
    ]

    nav_links = ""
    for label, href, key in nav_items:
        active_class = ' class="active"' if key == active else ""
        nav_links += f'<a href="{href}"{active_class}>{label}</a>'

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} — ML Gestión</title>
    <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🛒</text></svg>">
    <style>{GLOBAL_CSS}</style>
</head>
<body>
    <nav class="navbar">
        <a href="/" class="brand">
            <div class="brand-logo">🛒</div>
            <span class="brand-name">ML Gestión</span>
            <span class="brand-tag">Pro</span>
        </a>
        <div class="nav-links">
            {nav_links}
        </div>
    </nav>

    <main class="container">
        {content}
    </main>

    <div class="mobile-nav">
        <div class="nav-links">
            {nav_links}
        </div>
    </div>

    {MODAL_HTML}
    {MODAL_JS}
</body>
</html>"""
