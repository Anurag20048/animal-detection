from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"


def test_frontend_dashboard_files_exist():
    assert (FRONTEND / "index.html").is_file()
    assert (FRONTEND / "css" / "style.css").is_file()
    assert (FRONTEND / "js" / "api.js").is_file()
    assert (FRONTEND / "js" / "app.js").is_file()
    assert (FRONTEND / "js" / "data.js").is_file()


def test_frontend_uses_supported_backend_routes():
    app = (FRONTEND / "js" / "app.js").read_text(encoding="utf-8")
    api = (FRONTEND / "js" / "api.js").read_text(encoding="utf-8")
    for route in ["/stats", "/api/animals/", "/api/detections/", "/api/analytics/", "/api/auth/login/"]:
        assert route in app
    assert "Bearer" in api


def test_frontend_does_not_ship_default_password():
    app = (FRONTEND / "js" / "app.js").read_text(encoding="utf-8")
    index = (FRONTEND / "index.html").read_text(encoding="utf-8")
    assert "Demo@123" not in app
    assert "Demo@123" not in index
