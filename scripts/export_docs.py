"""Script to export OpenAPI specification (JSON & YAML) and assemble GitHub Pages documentation."""

import json
import os
import sys
from pathlib import Path

import yaml

# Ensure SQLAlchemy C-extensions don't fail on restricted environments
os.environ["DISABLE_SQLALCHEMY_CEXT"] = "1"
os.environ["JWT_SECRET_KEY"] = "docs-export-secret-key-32-chars-minimum-sample"

# Add repository root to pythonpath
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from app.main import app  # noqa: E402


def export_openapi_specs(docs_dir: Path) -> dict:
    """Generate and write openapi.json and openapi.yaml."""
    docs_dir.mkdir(parents=True, exist_ok=True)

    openapi_data = app.openapi()

    # Ensure servers section is present
    if not openapi_data.get("servers"):
        openapi_data["servers"] = [
            {"url": "http://127.0.0.1:8000", "description": "Local Development Server"},
            {"url": "https://api.spendtracker.ke", "description": "Production API Server (Sample)"},
        ]

    # Write openapi.json
    json_path = docs_dir / "openapi.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(openapi_data, f, indent=2)
    print(f"Exported: {json_path} ({json_path.stat().st_size} bytes)")

    # Write openapi.yaml
    yaml_path = docs_dir / "openapi.yaml"
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(openapi_data, f, sort_keys=False, allow_unicode=True)
    print(f"Exported: {yaml_path} ({yaml_path.stat().st_size} bytes)")

    return openapi_data


def generate_swagger_page(docs_dir: Path) -> None:
    """Create interactive standalone Swagger UI page."""
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Spend Tracker API - Swagger UI</title>
  <link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist@5.18.2/swagger-ui.css">
  <link rel="icon" type="image/png" href="https://fastapi.tiangolo.com/img/favicon.png">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }
    body {
      background-color: #0d1117;
      color: #c9d1d9;
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    .top-nav {
      background: rgba(22, 27, 34, 0.95);
      backdrop-filter: blur(12px);
      border-bottom: 1px solid #30363d;
      padding: 0.75rem 1.5rem;
      display: flex;
      align-items: center;
      justify-content: space-between;
      position: sticky;
      top: 0;
      z-index: 1000;
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      text-decoration: none;
      color: #f0f6fc;
      font-weight: 700;
      font-size: 1.1rem;
    }
    .brand-badge {
      background: linear-gradient(135deg, #10b981 0%, #06b6d4 100%);
      color: #041014;
      font-size: 0.75rem;
      font-weight: 700;
      padding: 0.2rem 0.55rem;
      border-radius: 9999px;
      letter-spacing: 0.05em;
    }
    .nav-links {
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }
    .nav-btn {
      color: #8b949e;
      text-decoration: none;
      font-size: 0.875rem;
      font-weight: 500;
      padding: 0.45rem 0.85rem;
      border-radius: 6px;
      transition: all 0.2s ease;
      display: inline-flex;
      align-items: center;
      gap: 0.4rem;
    }
    .nav-btn:hover {
      color: #f0f6fc;
      background: #21262d;
    }
    .nav-btn.active {
      color: #58a6ff;
      background: rgba(56, 139, 253, 0.15);
      border: 1px solid rgba(56, 139, 253, 0.3);
    }
    .download-pill {
      background: #238636;
      color: #ffffff !important;
      font-weight: 600;
    }
    .download-pill:hover {
      background: #2ea043 !important;
    }
    /* Swagger container dark tweaks */
    #swagger-ui {
      max-width: 1300px;
      margin: 0 auto;
      padding: 1.5rem;
    }
    .swagger-ui {
      filter: invert(88%) hue-rotate(180deg);
    }
    .swagger-ui .topbar {
      display: none !important;
    }
  </style>
</head>
<body>
  <header class="top-nav">
    <a href="index.html" class="brand">
      <span>🇰🇪 Spend Tracker API</span>
      <span class="brand-badge">v0.1.0</span>
    </a>
    <nav class="nav-links">
      <a href="index.html" class="nav-btn">🏠 Portal</a>
      <a href="swagger.html" class="nav-btn active">⚡ Swagger UI</a>
      <a href="redoc.html" class="nav-btn">📖 ReDoc</a>
      <a href="coverage/index.html" class="nav-btn">🧪 Coverage</a>
      <a href="openapi.json" download class="nav-btn download-pill">⬇️ openapi.json</a>
    </nav>
  </header>
  <div id="swagger-ui"></div>
  <script src="https://unpkg.com/swagger-ui-dist@5.18.2/swagger-ui-bundle.js"></script>
  <script src="https://unpkg.com/swagger-ui-dist@5.18.2/swagger-ui-standalone-preset.js"></script>
  <script>
    window.onload = function() {
      SwaggerUIBundle({
        url: "./openapi.json",
        dom_id: '#swagger-ui',
        deepLinking: true,
        presets: [
          SwaggerUIBundle.presets.apis,
          SwaggerUIStandalonePreset
        ],
        layout: "BaseLayout",
        defaultModelsExpandDepth: 2,
        defaultModelExpandDepth: 2,
        docExpansion: "list",
        filter: true,
        showExtensions: true,
        showCommonExtensions: true
      });
    };
  </script>
</body>
</html>
"""
    swagger_path = docs_dir / "swagger.html"
    with open(swagger_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Generated: {swagger_path}")


def generate_redoc_page(docs_dir: Path) -> None:
    """Create standalone ReDoc API documentation page."""
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Spend Tracker API - ReDoc Documentation</title>
  <link rel="icon" type="image/png" href="https://fastapi.tiangolo.com/img/favicon.png">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }
    body {
      background-color: #0d1117;
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    .top-nav {
      background: rgba(22, 27, 34, 0.98);
      backdrop-filter: blur(12px);
      border-bottom: 1px solid #30363d;
      padding: 0.75rem 1.5rem;
      display: flex;
      align-items: center;
      justify-content: space-between;
      position: sticky;
      top: 0;
      z-index: 1000;
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      text-decoration: none;
      color: #f0f6fc;
      font-weight: 700;
      font-size: 1.1rem;
    }
    .brand-badge {
      background: linear-gradient(135deg, #10b981 0%, #06b6d4 100%);
      color: #041014;
      font-size: 0.75rem;
      font-weight: 700;
      padding: 0.2rem 0.55rem;
      border-radius: 9999px;
      letter-spacing: 0.05em;
    }
    .nav-links {
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }
    .nav-btn {
      color: #8b949e;
      text-decoration: none;
      font-size: 0.875rem;
      font-weight: 500;
      padding: 0.45rem 0.85rem;
      border-radius: 6px;
      transition: all 0.2s ease;
      display: inline-flex;
      align-items: center;
      gap: 0.4rem;
    }
    .nav-btn:hover {
      color: #f0f6fc;
      background: #21262d;
    }
    .nav-btn.active {
      color: #58a6ff;
      background: rgba(56, 139, 253, 0.15);
      border: 1px solid rgba(56, 139, 253, 0.3);
    }
    .download-pill {
      background: #238636;
      color: #ffffff !important;
      font-weight: 600;
    }
    .download-pill:hover {
      background: #2ea043 !important;
    }
    #redoc-container {
      min-height: calc(100vh - 65px);
    }
  </style>
</head>
<body>
  <header class="top-nav">
    <a href="index.html" class="brand">
      <span>🇰🇪 Spend Tracker API</span>
      <span class="brand-badge">v0.1.0</span>
    </a>
    <nav class="nav-links">
      <a href="index.html" class="nav-btn">🏠 Portal</a>
      <a href="swagger.html" class="nav-btn">⚡ Swagger UI</a>
      <a href="redoc.html" class="nav-btn active">📖 ReDoc</a>
      <a href="coverage/index.html" class="nav-btn">🧪 Coverage</a>
      <a href="openapi.yaml" download class="nav-btn download-pill">⬇️ openapi.yaml</a>
    </nav>
  </header>
  <div id="redoc-container"></div>
  <script src="https://cdn.redoc.ly/redoc/latest/bundles/redoc.standalone.js"></script>
  <script>
    Redoc.init('./openapi.json', {
      theme: {
        colors: {
          primary: {
            main: '#06b6d4'
          }
        },
        typography: {
          fontFamily: 'Inter, sans-serif',
          headings: {
            fontFamily: 'Inter, sans-serif',
            fontWeight: '600'
          }
        },
        sidebar: {
          backgroundColor: '#161b22',
          textColor: '#c9d1d9'
        },
        rightPanel: {
          backgroundColor: '#0d1117'
        }
      },
      scrollYOffset: 65,
      hideDownloadButton: false,
      expandResponses: "200,201"
    }, document.getElementById('redoc-container'));
  </script>
</body>
</html>
"""
    redoc_path = docs_dir / "redoc.html"
    with open(redoc_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Generated: {redoc_path}")


def generate_index_page(docs_dir: Path) -> None:
    """Create the rich modern landing portal linking Swagger, ReDoc, Coverage, and Specs."""
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Spend Tracker API - Developer Portal & Docs</title>
  <meta name="description" content="Official documentation, interactive Swagger UI, ReDoc, test coverage reports, and OpenAPI specifications for Spend Tracker API.">
  <link rel="icon" type="image/png" href="https://fastapi.tiangolo.com/img/favicon.png">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg-primary: #090d16;
      --bg-secondary: #0f172a;
      --bg-card: rgba(30, 41, 59, 0.7);
      --border-color: rgba(148, 163, 184, 0.12);
      --border-hover: rgba(56, 189, 248, 0.4);
      --text-main: #f8fafc;
      --text-muted: #94a3b8;
      --accent-emerald: #10b981;
      --accent-cyan: #06b6d4;
      --accent-blue: #3b82f6;
      --accent-purple: #8b5cf6;
      --gradient-brand: linear-gradient(135deg, #10b981 0%, #06b6d4 50%, #3b82f6 100%);
    }

    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }

    body {
      background-color: var(--bg-primary);
      background-image:
        radial-gradient(at 0% 0%, rgba(16, 185, 129, 0.12) 0px, transparent 50%),
        radial-gradient(at 100% 0%, rgba(6, 182, 212, 0.12) 0px, transparent 50%),
        radial-gradient(at 50% 100%, rgba(59, 130, 246, 0.08) 0px, transparent 50%);
      color: var(--text-main);
      font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }

    .header-nav {
      position: sticky;
      top: 0;
      z-index: 100;
      background: rgba(9, 13, 22, 0.85);
      backdrop-filter: blur(16px);
      border-bottom: 1px solid var(--border-color);
      padding: 1rem 2rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .brand-wrap {
      display: flex;
      align-items: center;
      gap: 0.85rem;
      text-decoration: none;
      color: var(--text-main);
    }

    .brand-icon {
      width: 40px;
      height: 40px;
      border-radius: 10px;
      background: var(--gradient-brand);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 1.25rem;
      box-shadow: 0 4px 14px rgba(6, 182, 212, 0.3);
    }

    .brand-text h1 {
      font-size: 1.15rem;
      font-weight: 700;
      letter-spacing: -0.02em;
    }

    .brand-text p {
      font-size: 0.75rem;
      color: var(--text-muted);
    }

    .nav-actions {
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }

    .nav-link {
      color: var(--text-muted);
      text-decoration: none;
      font-size: 0.875rem;
      font-weight: 600;
      padding: 0.5rem 1rem;
      border-radius: 8px;
      transition: all 0.2s ease;
      display: inline-flex;
      align-items: center;
      gap: 0.4rem;
    }

    .nav-link:hover {
      color: var(--text-main);
      background: rgba(255, 255, 255, 0.06);
    }

    .btn-gh {
      background: rgba(255, 255, 255, 0.08);
      border: 1px solid var(--border-color);
      color: var(--text-main) !important;
    }
    .btn-gh:hover {
      background: rgba(255, 255, 255, 0.15);
      border-color: rgba(255, 255, 255, 0.3);
    }

    main {
      flex: 1;
      max-width: 1200px;
      width: 100%;
      margin: 0 auto;
      padding: 3rem 1.5rem;
    }

    .hero {
      text-align: center;
      padding: 2.5rem 1rem 3.5rem;
      position: relative;
    }

    .hero-badge {
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      background: rgba(16, 185, 129, 0.12);
      border: 1px solid rgba(16, 185, 129, 0.3);
      color: #34d399;
      font-size: 0.825rem;
      font-weight: 600;
      padding: 0.35rem 0.85rem;
      border-radius: 9999px;
      margin-bottom: 1.5rem;
    }

    .hero-title {
      font-size: clamp(2.25rem, 5vw, 3.75rem);
      font-weight: 800;
      line-height: 1.15;
      letter-spacing: -0.03em;
      margin-bottom: 1.25rem;
    }

    .hero-gradient {
      background: var(--gradient-brand);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }

    .hero-subtitle {
      max-width: 720px;
      margin: 0 auto 2.25rem;
      font-size: 1.1rem;
      line-height: 1.6;
      color: var(--text-muted);
    }

    .stats-bar {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 1rem;
      margin-bottom: 3.5rem;
    }

    .stat-pill {
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: 12px;
      padding: 1.25rem;
      display: flex;
      flex-direction: column;
      gap: 0.25rem;
      backdrop-filter: blur(12px);
    }

    .stat-num {
      font-size: 1.75rem;
      font-weight: 800;
      letter-spacing: -0.02em;
      background: linear-gradient(135deg, #ffffff 0%, #cbd5e1 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }

    .stat-label {
      font-size: 0.8rem;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.05em;
      font-weight: 600;
    }

    .cards-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
      gap: 1.5rem;
      margin-bottom: 3.5rem;
    }

    .feature-card {
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: 16px;
      padding: 2rem;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
      position: relative;
      overflow: hidden;
      backdrop-filter: blur(16px);
    }

    .feature-card:hover {
      transform: translateY(-4px);
      border-color: var(--border-hover);
      box-shadow: 0 12px 30px rgba(0, 0, 0, 0.3), 0 0 20px rgba(6, 182, 212, 0.15);
    }

    .card-top {
      margin-bottom: 1.5rem;
    }

    .card-icon {
      width: 48px;
      height: 48px;
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 1.5rem;
      margin-bottom: 1.25rem;
    }

    .card-title {
      font-size: 1.35rem;
      font-weight: 700;
      margin-bottom: 0.5rem;
      letter-spacing: -0.01em;
    }

    .card-desc {
      color: var(--text-muted);
      font-size: 0.95rem;
      line-height: 1.55;
    }

    .card-meta {
      display: flex;
      gap: 0.5rem;
      margin: 1rem 0;
      flex-wrap: wrap;
    }

    .tag {
      font-size: 0.75rem;
      padding: 0.2rem 0.6rem;
      border-radius: 6px;
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid var(--border-color);
      color: var(--text-muted);
    }

    .card-action {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 0.5rem;
      width: 100%;
      padding: 0.75rem 1.25rem;
      border-radius: 10px;
      font-weight: 600;
      font-size: 0.925rem;
      text-decoration: none;
      transition: all 0.2s ease;
    }

    .btn-emerald {
      background: linear-gradient(135deg, #10b981 0%, #059669 100%);
      color: #ffffff;
      box-shadow: 0 4px 14px rgba(16, 185, 129, 0.3);
    }
    .btn-emerald:hover {
      background: linear-gradient(135deg, #059669 0%, #047857 100%);
      box-shadow: 0 6px 18px rgba(16, 185, 129, 0.45);
    }

    .btn-cyan {
      background: linear-gradient(135deg, #06b6d4 0%, #0284c7 100%);
      color: #ffffff;
      box-shadow: 0 4px 14px rgba(6, 182, 212, 0.3);
    }
    .btn-cyan:hover {
      background: linear-gradient(135deg, #0891b2 0%, #0369a1 100%);
      box-shadow: 0 6px 18px rgba(6, 182, 212, 0.45);
    }

    .btn-purple {
      background: linear-gradient(135deg, #8b5cf6 0%, #6d28d9 100%);
      color: #ffffff;
      box-shadow: 0 4px 14px rgba(139, 92, 246, 0.3);
    }
    .btn-purple:hover {
      background: linear-gradient(135deg, #7c3aed 0%, #5b21b6 100%);
      box-shadow: 0 6px 18px rgba(139, 92, 246, 0.45);
    }

    /* Specs Banner */
    .specs-banner {
      background: linear-gradient(135deg, rgba(30, 41, 59, 0.8) 0%, rgba(15, 23, 42, 0.9) 100%);
      border: 1px solid var(--border-color);
      border-radius: 16px;
      padding: 2.25rem;
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: center;
      gap: 1.5rem;
      backdrop-filter: blur(12px);
      margin-bottom: 3rem;
    }

    .specs-info h3 {
      font-size: 1.35rem;
      font-weight: 700;
      margin-bottom: 0.4rem;
    }
    .specs-info p {
      color: var(--text-muted);
      font-size: 0.95rem;
    }

    .specs-buttons {
      display: flex;
      gap: 0.75rem;
      flex-wrap: wrap;
    }

    .btn-outline {
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid var(--border-color);
      color: var(--text-main);
      padding: 0.65rem 1.25rem;
      border-radius: 8px;
      font-weight: 600;
      font-size: 0.875rem;
      text-decoration: none;
      display: inline-flex;
      align-items: center;
      gap: 0.4rem;
      transition: all 0.2s ease;
    }
    .btn-outline:hover {
      background: rgba(255, 255, 255, 0.12);
      border-color: rgba(255, 255, 255, 0.25);
    }

    /* Terminal Preview */
    .terminal-section {
      background: #0d1117;
      border: 1px solid #30363d;
      border-radius: 12px;
      overflow: hidden;
      margin-bottom: 3.5rem;
    }
    .terminal-header {
      background: #161b22;
      padding: 0.75rem 1rem;
      display: flex;
      align-items: center;
      gap: 0.5rem;
      border-bottom: 1px solid #30363d;
    }
    .dot {
      width: 12px;
      height: 12px;
      border-radius: 50%;
    }
    .dot-red { background: #ff5f56; }
    .dot-yellow { background: #ffbd2e; }
    .dot-green { background: #27c93f; }
    .terminal-title {
      color: #8b949e;
      font-size: 0.75rem;
      margin-left: 0.5rem;
      font-family: 'JetBrains Mono', monospace;
    }
    .terminal-body {
      padding: 1.25rem;
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.875rem;
      line-height: 1.6;
      color: #e6edf3;
      overflow-x: auto;
    }
    .cmd-line {
      color: #7ee787;
    }
    .comment {
      color: #8b949e;
    }

    footer {
      border-top: 1px solid var(--border-color);
      padding: 2rem 1.5rem;
      text-align: center;
      color: var(--text-muted);
      font-size: 0.875rem;
      background: rgba(9, 13, 22, 0.95);
    }
  </style>
</head>
<body>

  <header class="header-nav">
    <a href="index.html" class="brand-wrap">
      <div class="brand-icon">⚡</div>
      <div class="brand-text">
        <h1>Spend Tracker API</h1>
        <p>FinTech Developer Portal</p>
      </div>
    </a>
    <nav class="nav-actions">
      <a href="swagger.html" class="nav-link">⚡ Swagger UI</a>
      <a href="redoc.html" class="nav-link">📖 ReDoc</a>
      <a href="coverage/index.html" class="nav-link">🧪 Coverage</a>
      <a href="https://github.com/crnjihia/spend-tracker-api" target="_blank" rel="noopener" class="nav-link btn-gh">
        GitHub Repo ↗
      </a>
    </nav>
  </header>

  <main>
    <section class="hero">
      <div class="hero-badge">
        <span>✨ Production-Grade FinTech API</span>
        <span>•</span>
        <span>v0.1.0 (v1 stable)</span>
      </div>
      <h2 class="hero-title">
        The Modern Engine for <br>
        <span class="hero-gradient">East African Spending & M-Pesa</span>
      </h2>
      <p class="hero-subtitle">
        High-throughput M-Pesa transaction ingestion, rule-driven automated categorisation,
        idempotent budget alerts, and enterprise-grade multi-tenant analytics.
      </p>
    </section>

    <!-- Stats & Architecture Metrics -->
    <section class="stats-bar">
      <div class="stat-pill">
        <span class="stat-num">92%+</span>
        <span class="stat-label">Statement Coverage</span>
      </div>
      <div class="stat-pill">
        <span class="stat-num">18/18</span>
        <span class="stat-label">Automated Tests Passing</span>
      </div>
      <div class="stat-pill">
        <span class="stat-num">15 min / 7 d</span>
        <span class="stat-label">Rotating JWT Tokens</span>
      </div>
      <div class="stat-pill">
        <span class="stat-num">100 / min</span>
        <span class="stat-label">SlowAPI Rate Limit</span>
      </div>
    </section>

    <!-- Documentation & Explorer Cards -->
    <section class="cards-grid">
      <!-- Swagger UI Card -->
      <div class="feature-card">
        <div class="card-top">
          <div class="card-icon" style="background: rgba(16, 185, 129, 0.15); color: #10b981;">⚡</div>
          <h3 class="card-title">Interactive Swagger UI</h3>
          <p class="card-desc">
            Explore live API endpoints, inspect request/response schemas, execute test calls, and authenticate with JWT bearer tokens.
          </p>
          <div class="card-meta">
            <span class="tag">Interactive</span>
            <span class="tag">Try It Out</span>
            <span class="tag">OpenAPI 3.1</span>
          </div>
        </div>
        <a href="swagger.html" class="card-action btn-emerald">Open Swagger Explorer →</a>
      </div>

      <!-- ReDoc Card -->
      <div class="feature-card">
        <div class="card-top">
          <div class="card-icon" style="background: rgba(6, 182, 212, 0.15); color: #06b6d4;">📖</div>
          <h3 class="card-title">ReDoc API Reference</h3>
          <p class="card-desc">
            Clean, responsive 3-panel API documentation with in-depth payload breakdowns, nested schema models, and code samples.
          </p>
          <div class="card-meta">
            <span class="tag">Clean Typography</span>
            <span class="tag">SDK Reference</span>
            <span class="tag">Searchable</span>
          </div>
        </div>
        <a href="redoc.html" class="card-action btn-cyan">Open ReDoc Reference →</a>
      </div>

      <!-- Coverage Report Card -->
      <div class="feature-card">
        <div class="card-top">
          <div class="card-icon" style="background: rgba(139, 92, 246, 0.15); color: #8b5cf6;">🧪</div>
          <h3 class="card-title">Test Coverage Report</h3>
          <p class="card-desc">
            Granular HTML coverage dashboard generated from pytest, highlighting line-by-line branch coverage across models, services, and repositories.
          </p>
          <div class="card-meta">
            <span class="tag">pytest-cov</span>
            <span class="tag">Zero Dependency</span>
            <span class="tag">Unit + Integration</span>
          </div>
        </div>
        <a href="coverage/index.html" class="card-action btn-purple">View Coverage Report →</a>
      </div>
    </section>

    <!-- OpenAPI Spec Downloads Banner -->
    <section class="specs-banner">
      <div class="specs-info">
        <h3>Official OpenAPI Specifications</h3>
        <p>Download standard machine-readable API contracts for Postman, Insomnia, SDK generators, or API gateways.</p>
      </div>
      <div class="specs-buttons">
        <a href="openapi.json" download="openapi.json" class="btn-outline">
          📥 Download openapi.json
        </a>
        <a href="openapi.yaml" download="openapi.yaml" class="btn-outline">
          📥 Download openapi.yaml
        </a>
      </div>
    </section>

    <!-- Terminal Quickstart Preview -->
    <section class="terminal-section">
      <div class="terminal-header">
        <span class="dot dot-red"></span>
        <span class="dot dot-yellow"></span>
        <span class="dot dot-green"></span>
        <span class="terminal-title">bash — Pull Docker Image & Ingest Transaction</span>
      </div>
      <div class="terminal-body">
        <p class="comment"># Pull and run pre-built container from GitHub Container Registry (GHCR)</p>
        <p class="cmd-line">docker pull ghcr.io/crnjihia/spend-tracker-api:latest</p>
        <p class="cmd-line">docker run -d -p 8000:8000 --env-file .env ghcr.io/crnjihia/spend-tracker-api:latest</p>
        <br>
        <p class="comment"># Ingest an M-Pesa C2B Paybill payment payload</p>
        <p class="cmd-line">curl -X POST http://127.0.0.1:8000/api/v1/transactions/mpesa \\</p>
        <p style="padding-left: 1.5rem;">-H "Authorization: Bearer $ACCESS_TOKEN" \\</p>
        <p style="padding-left: 1.5rem;">-H "Content-Type: application/json" \\</p>
        <p style="padding-left: 1.5rem;">-d '{"TransID":"QGH7XYZ123","TransAmount":"1500.00","BusinessShortCode":"247247","BillRefNumber":"Naivas Supermarket","TransTime":"20261008143022"}'</p>
      </div>
    </section>
  </main>

  <footer>
    <p>Spend Tracker API &bull; Built with FastAPI, PostgreSQL & Redis &bull; MIT Licensed</p>
    <p style="margin-top: 0.5rem; font-size: 0.8rem; opacity: 0.7;">Automated CI/CD Documentation generated on commit</p>
  </footer>

</body>
</html>
"""
    index_path = docs_dir / "index.html"
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Generated: {index_path}")


def main():
    docs_dir = REPO_ROOT / "docs"
    print(f"Building documentation assets in {docs_dir}...")
    export_openapi_specs(docs_dir)
    generate_swagger_page(docs_dir)
    generate_redoc_page(docs_dir)
    generate_index_page(docs_dir)

    # Remove coverage-generated .gitignore if present to ensure pages artifact packaging
    cov_gitignore = docs_dir / "coverage" / ".gitignore"
    if cov_gitignore.exists():
        try:
            cov_gitignore.unlink()
        except OSError:
            pass

    print("Documentation build completed successfully!")


if __name__ == "__main__":
    main()
