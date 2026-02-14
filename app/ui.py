"""Componentes de UI compartidos - layout base, nav, estilos."""


def base_layout(title: str, content: str, active: str = "") -> str:
    """Genera el HTML completo con layout, nav y estilos."""
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
    <title>{title} - ML Gestión</title>
    <style>
        :root {{
            --bg: #f4f5f7;
            --surface: #ffffff;
            --surface-hover: #fafbfc;
            --primary: #1e293b;
            --primary-light: #334155;
            --accent: #3b82f6;
            --accent-soft: #eff6ff;
            --text: #1e293b;
            --text-secondary: #64748b;
            --text-muted: #94a3b8;
            --border: #e2e8f0;
            --success: #10b981;
            --success-bg: #ecfdf5;
            --warning: #f59e0b;
            --warning-bg: #fffbeb;
            --danger: #ef4444;
            --danger-bg: #fef2f2;
            --radius: 12px;
            --radius-sm: 8px;
            --shadow: 0 1px 3px rgba(0,0,0,0.04), 0 1px 2px rgba(0,0,0,0.06);
            --shadow-md: 0 4px 6px rgba(0,0,0,0.04), 0 2px 4px rgba(0,0,0,0.06);
        }}

        * {{ margin: 0; padding: 0; box-sizing: border-box; }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Inter, Roboto, sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.5;
            -webkit-font-smoothing: antialiased;
        }}

        /* ── NAV ── */
        .navbar {{
            background: var(--primary);
            padding: 0 24px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            height: 60px;
            position: sticky;
            top: 0;
            z-index: 100;
        }}

        .navbar .brand {{
            color: #fff;
            font-size: 18px;
            font-weight: 700;
            letter-spacing: -0.3px;
            text-decoration: none;
            display: flex;
            align-items: center;
            gap: 10px;
        }}

        .navbar .brand span {{
            background: var(--accent);
            color: #fff;
            font-size: 11px;
            padding: 2px 8px;
            border-radius: 4px;
            font-weight: 600;
        }}

        .nav-links {{
            display: flex;
            gap: 4px;
        }}

        .nav-links a {{
            color: #94a3b8;
            text-decoration: none;
            padding: 8px 16px;
            border-radius: var(--radius-sm);
            font-size: 14px;
            font-weight: 500;
            transition: all 0.15s ease;
        }}

        .nav-links a:hover {{
            color: #fff;
            background: rgba(255,255,255,0.08);
        }}

        .nav-links a.active {{
            color: #fff;
            background: rgba(255,255,255,0.12);
        }}

        /* ── MOBILE NAV ── */
        .mobile-nav {{
            display: none;
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background: var(--surface);
            border-top: 1px solid var(--border);
            padding: 8px 0;
            padding-bottom: max(8px, env(safe-area-inset-bottom));
            z-index: 100;
        }}

        .mobile-nav .nav-links {{
            justify-content: center;
            gap: 0;
        }}

        .mobile-nav .nav-links a {{
            color: var(--text-muted);
            flex: 1;
            text-align: center;
            font-size: 12px;
            padding: 6px 4px;
            border-radius: 0;
        }}

        .mobile-nav .nav-links a.active {{
            color: var(--accent);
            background: transparent;
            font-weight: 600;
        }}

        /* ── LAYOUT ── */
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 24px 20px;
        }}

        .page-title {{
            font-size: 24px;
            font-weight: 700;
            color: var(--text);
            margin-bottom: 4px;
            letter-spacing: -0.5px;
        }}

        .page-subtitle {{
            font-size: 14px;
            color: var(--text-secondary);
            margin-bottom: 24px;
        }}

        /* ── CARDS GRID ── */
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }}

        .stat-card {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            padding: 20px;
            box-shadow: var(--shadow);
        }}

        .stat-card .stat-label {{
            font-size: 13px;
            color: var(--text-secondary);
            font-weight: 500;
            margin-bottom: 8px;
        }}

        .stat-card .stat-value {{
            font-size: 32px;
            font-weight: 700;
            color: var(--text);
            letter-spacing: -1px;
            line-height: 1;
        }}

        .stat-card .stat-detail {{
            font-size: 12px;
            color: var(--text-muted);
            margin-top: 6px;
        }}

        .stat-card.accent {{
            border-left: 3px solid var(--accent);
        }}

        .stat-card.success {{
            border-left: 3px solid var(--success);
        }}

        .stat-card.warning {{
            border-left: 3px solid var(--warning);
        }}

        .stat-card.danger {{
            border-left: 3px solid var(--danger);
        }}

        /* ── TABLE ── */
        .table-wrapper {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            box-shadow: var(--shadow);
            overflow: hidden;
        }}

        .table-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 16px 20px;
            border-bottom: 1px solid var(--border);
        }}

        .table-header h2 {{
            font-size: 16px;
            font-weight: 600;
        }}

        .btn {{
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
            transition: all 0.15s ease;
        }}

        .btn:hover {{
            background: var(--surface-hover);
            box-shadow: var(--shadow);
        }}

        .btn-primary {{
            background: var(--accent);
            color: #fff;
            border-color: var(--accent);
        }}

        .btn-primary:hover {{
            background: #2563eb;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
        }}

        th {{
            padding: 12px 20px;
            text-align: left;
            font-size: 12px;
            font-weight: 600;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            border-bottom: 1px solid var(--border);
            background: var(--bg);
        }}

        td {{
            padding: 14px 20px;
            font-size: 14px;
            border-bottom: 1px solid var(--border);
            vertical-align: top;
        }}

        tr:last-child td {{
            border-bottom: none;
        }}

        tr:hover td {{
            background: var(--surface-hover);
        }}

        /* ── BADGES ── */
        .badge {{
            display: inline-flex;
            align-items: center;
            gap: 4px;
            padding: 3px 10px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 500;
        }}

        .badge-success {{ background: var(--success-bg); color: #065f46; }}
        .badge-warning {{ background: var(--warning-bg); color: #92400e; }}
        .badge-danger {{ background: var(--danger-bg); color: #991b1b; }}
        .badge-neutral {{ background: var(--bg); color: var(--text-secondary); }}
        .badge-accent {{ background: var(--accent-soft); color: #1d4ed8; }}

        /* ── EMPTY STATE ── */
        .empty-state {{
            text-align: center;
            padding: 60px 20px;
            color: var(--text-muted);
        }}

        .empty-state .icon {{
            font-size: 48px;
            margin-bottom: 12px;
            opacity: 0.4;
        }}

        .empty-state p {{
            font-size: 16px;
        }}

        /* ── CARDS LIST (mobile-friendly alternative to table) ── */
        .order-cards {{
            display: none;
        }}

        .order-card {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            padding: 16px;
            margin-bottom: 12px;
            box-shadow: var(--shadow);
        }}

        .order-card-header {{
            display: flex;
            justify-content: space-between;
            align-items: start;
            margin-bottom: 12px;
        }}

        .order-card-header .order-id {{
            font-weight: 700;
            font-size: 15px;
        }}

        .order-card-header .order-date {{
            font-size: 12px;
            color: var(--text-muted);
        }}

        .order-card-body {{
            display: flex;
            flex-direction: column;
            gap: 8px;
        }}

        .order-card-row {{
            display: flex;
            justify-content: space-between;
            font-size: 13px;
        }}

        .order-card-row .label {{
            color: var(--text-secondary);
        }}

        .order-card-products {{
            font-size: 13px;
            padding: 8px 0;
            border-top: 1px solid var(--border);
            border-bottom: 1px solid var(--border);
            margin: 4px 0;
        }}

        .order-card-products div {{
            padding: 2px 0;
        }}

        /* ── LOADING ── */
        .loading {{
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 40px;
            color: var(--text-muted);
            gap: 8px;
        }}

        .spinner {{
            width: 20px;
            height: 20px;
            border: 2px solid var(--border);
            border-top-color: var(--accent);
            border-radius: 50%;
            animation: spin 0.6s linear infinite;
        }}

        @keyframes spin {{
            to {{ transform: rotate(360deg); }}
        }}

        /* ── RESPONSIVE ── */
        @media (max-width: 768px) {{
            .navbar .nav-links {{
                display: none;
            }}

            .mobile-nav {{
                display: block;
            }}

            body {{
                padding-bottom: 70px;
            }}

            .container {{
                padding: 16px 12px;
            }}

            .page-title {{
                font-size: 20px;
            }}

            .stats {{
                grid-template-columns: repeat(2, 1fr);
                gap: 10px;
            }}

            .stat-card {{
                padding: 14px;
            }}

            .stat-card .stat-value {{
                font-size: 24px;
            }}

            /* Hide table, show cards on mobile */
            .table-desktop {{
                display: none;
            }}

            .order-cards {{
                display: block;
            }}

            .table-header {{
                padding: 12px 16px;
            }}
        }}

        @media (max-width: 400px) {{
            .stats {{
                grid-template-columns: 1fr 1fr;
                gap: 8px;
            }}

            .stat-card .stat-value {{
                font-size: 22px;
            }}
        }}
    </style>
</head>
<body>
    <nav class="navbar">
        <a href="/" class="brand">ML Gestión <span>v1</span></a>
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
</body>
</html>"""
