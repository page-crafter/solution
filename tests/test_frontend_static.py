from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from page_crafter.api.main import create_app
from page_crafter.shared.settings.app import get_settings


@pytest.fixture(autouse=True)
def clear_settings_cache() -> Iterator[None]:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def write_frontend_dist(path: Path) -> None:
    assets_dir = path / "assets"
    assets_dir.mkdir(parents=True)
    (path / "index.html").write_text("<div id=\"app\">Page Crafter</div>", encoding="utf-8")
    (path / "config.json").write_text('{"backend":{"baseUrl":""}}', encoding="utf-8")
    (assets_dir / "app.js").write_text("console.log('page-crafter')", encoding="utf-8")


def test_fastapi_serves_frontend_and_spa_fallback(monkeypatch, tmp_path) -> None:
    dist_dir = tmp_path / "dist"
    write_frontend_dist(dist_dir)
    monkeypatch.setenv("FRONTEND_DIST_DIR", str(dist_dir))

    client = TestClient(create_app())

    index_response = client.get("/")
    assert index_response.status_code == 200
    assert "Page Crafter" in index_response.text

    spa_response = client.get("/pages/123")
    assert spa_response.status_code == 200
    assert "Page Crafter" in spa_response.text

    asset_response = client.get("/assets/app.js")
    assert asset_response.status_code == 200
    assert "page-crafter" in asset_response.text


def test_frontend_config_is_not_cached(monkeypatch, tmp_path) -> None:
    dist_dir = tmp_path / "dist"
    write_frontend_dist(dist_dir)
    monkeypatch.setenv("FRONTEND_DIST_DIR", str(dist_dir))

    response = TestClient(create_app()).get("/config.json")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"


def test_api_404_is_not_rewritten_to_frontend(monkeypatch, tmp_path) -> None:
    dist_dir = tmp_path / "dist"
    write_frontend_dist(dist_dir)
    monkeypatch.setenv("FRONTEND_DIST_DIR", str(dist_dir))

    client = TestClient(create_app())

    docs_response = client.get("/docs")
    assert docs_response.status_code == 200

    response = client.get("/api/unknown")

    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}
