"""Unit tests for /api/v1/api-tester/* endpoints."""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app, raise_server_exceptions=False)


class TestProxy:
    def test_proxy_get_success(self):
        """Proxy forwards GET and returns status/body/elapsed."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.headers = {"content-type": "application/json"}
        mock_resp.text = '{"status": "ok"}'

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.request = AsyncMock(return_value=mock_resp)

        with patch("src.api.routers.api_tester.httpx.AsyncClient", return_value=mock_client):
            resp = client.post(
                "/api/v1/api-tester/proxy",
                data={"config": json.dumps({"method": "GET", "url": "http://example.com/api"})},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status_code"] == 200
        assert data["body"] == '{"status": "ok"}'
        assert data["elapsed_ms"] >= 0

    def test_proxy_connection_error_returns_502(self):
        """Connection failure returns 502."""
        import httpx as _httpx

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.request = AsyncMock(side_effect=_httpx.ConnectError("refused"))

        with patch("src.api.routers.api_tester.httpx.AsyncClient", return_value=mock_client):
            resp = client.post(
                "/api/v1/api-tester/proxy",
                data={"config": json.dumps({"method": "GET", "url": "http://unreachable"})},
            )

        assert resp.status_code == 502

    def test_proxy_timeout_returns_504(self):
        """Timeout returns 504."""
        import httpx as _httpx

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.request = AsyncMock(side_effect=_httpx.TimeoutException("timeout"))

        with patch("src.api.routers.api_tester.httpx.AsyncClient", return_value=mock_client):
            resp = client.post(
                "/api/v1/api-tester/proxy",
                data={"config": json.dumps({"method": "GET", "url": "http://slow"})},
            )

        assert resp.status_code == 504

    def test_proxy_missing_config_returns_422(self):
        """Missing config form field returns 422."""
        resp = client.post("/api/v1/api-tester/proxy", data={})
        assert resp.status_code == 422


class TestSuiteCRUD:
    def test_list_suites_returns_list(self):
        resp = client.get("/api/v1/api-tester/suites")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_create_and_get_suite(self, tmp_path, monkeypatch):
        monkeypatch.setattr("src.api.routers.api_tester.SUITES_DIR", tmp_path)
        payload = {"name": "Test Suite", "base_url": "http://localhost", "requests": []}
        resp = client.post("/api/v1/api-tester/suites", json=payload)
        assert resp.status_code == 201
        suite_id = resp.json()["id"]

        resp2 = client.get(f"/api/v1/api-tester/suites/{suite_id}")
        assert resp2.status_code == 200
        assert resp2.json()["name"] == "Test Suite"

    def test_update_suite(self, tmp_path, monkeypatch):
        monkeypatch.setattr("src.api.routers.api_tester.SUITES_DIR", tmp_path)
        payload = {"name": "Original", "base_url": "http://localhost", "requests": []}
        suite_id = client.post("/api/v1/api-tester/suites", json=payload).json()["id"]

        update = {"name": "Updated", "base_url": "http://localhost", "requests": []}
        resp = client.put(f"/api/v1/api-tester/suites/{suite_id}", json=update)
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated"

    def test_delete_suite(self, tmp_path, monkeypatch):
        monkeypatch.setattr("src.api.routers.api_tester.SUITES_DIR", tmp_path)
        payload = {"name": "ToDelete", "base_url": "http://localhost", "requests": []}
        suite_id = client.post("/api/v1/api-tester/suites", json=payload).json()["id"]

        resp = client.delete(f"/api/v1/api-tester/suites/{suite_id}")
        assert resp.status_code == 204

        resp2 = client.get(f"/api/v1/api-tester/suites/{suite_id}")
        assert resp2.status_code == 404

    def test_get_nonexistent_suite_returns_404(self):
        resp = client.get("/api/v1/api-tester/suites/nonexistent-id")
        assert resp.status_code == 404
