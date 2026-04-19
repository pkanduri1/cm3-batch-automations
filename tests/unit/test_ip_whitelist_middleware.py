"""Unit tests for IPWhitelistMiddleware.

Note on TestClient: Starlette's TestClient sets ``request.client.host`` to the
string ``"testclient"`` (not a real IP).  Tests that need to exercise IP-based
allow/deny logic for a specific address therefore use ``trust_proxy=True`` and
supply an ``X-Forwarded-For`` header so the middleware reads a controllable IP.
Tests that verify the *no-whitelist* (open) path use the raw testclient host,
which is always allowed when the whitelist is empty.
"""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from src.api.middleware.ip_whitelist import IPWhitelistMiddleware


def make_app(whitelist, trust_proxy=False):
    """Create a minimal FastAPI app with IPWhitelistMiddleware attached.

    Args:
        whitelist: List of IP addresses and/or CIDR ranges to allow.
        trust_proxy: If True, use X-Forwarded-For header as client IP.

    Returns:
        FastAPI application with the middleware and a /ping route.
    """
    app = FastAPI()
    app.add_middleware(IPWhitelistMiddleware, whitelist=whitelist, trust_proxy=trust_proxy)

    @app.get("/ping")
    def ping():
        return {"ok": True}

    return app


def test_empty_whitelist_allows_all():
    """No whitelist configured — every IP (including 'testclient') is allowed."""
    app = make_app(whitelist=[])
    client = TestClient(app)
    response = client.get("/ping")
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_exact_ip_match_allowed():
    """An IP that exactly matches a whitelist entry is allowed (200)."""
    app = make_app(whitelist=["192.168.1.50"], trust_proxy=True)
    client = TestClient(app)
    response = client.get("/ping", headers={"X-Forwarded-For": "192.168.1.50"})
    assert response.status_code == 200


def test_exact_ip_not_in_whitelist_denied():
    """An IP not in the whitelist is blocked (403)."""
    app = make_app(whitelist=["10.0.0.1"], trust_proxy=True)
    client = TestClient(app)
    response = client.get("/ping", headers={"X-Forwarded-For": "192.168.1.99"})
    assert response.status_code == 403


def test_cidr_range_match_allowed():
    """An IP within a CIDR range whitelist entry is allowed (200)."""
    app = make_app(whitelist=["10.0.0.0/8"], trust_proxy=True)
    client = TestClient(app)
    response = client.get("/ping", headers={"X-Forwarded-For": "10.20.30.40"})
    assert response.status_code == 200


def test_cidr_range_no_match_denied():
    """An IP outside all CIDR ranges is blocked (403)."""
    app = make_app(whitelist=["10.0.0.0/8"], trust_proxy=True)
    client = TestClient(app)
    response = client.get("/ping", headers={"X-Forwarded-For": "172.16.0.1"})
    assert response.status_code == 403


def test_multiple_ranges():
    """IPs from each of multiple ranges are allowed; outside all ranges is denied."""
    app = make_app(whitelist=["10.0.0.0/8", "192.168.0.0/16"], trust_proxy=True)
    client = TestClient(app)

    # IP in first range
    response = client.get("/ping", headers={"X-Forwarded-For": "10.0.0.5"})
    assert response.status_code == 200

    # IP in second range
    response2 = client.get("/ping", headers={"X-Forwarded-For": "192.168.5.1"})
    assert response2.status_code == 200

    # IP outside both ranges
    response3 = client.get("/ping", headers={"X-Forwarded-For": "172.16.0.1"})
    assert response3.status_code == 403


def test_trust_proxy_x_forwarded_for():
    """When trust_proxy=True, X-Forwarded-For header is used as client IP."""
    # Whitelist only 192.168.1.50; provide matching header
    app = make_app(whitelist=["192.168.1.50"], trust_proxy=True)
    client = TestClient(app)
    response = client.get("/ping", headers={"X-Forwarded-For": "192.168.1.50"})
    assert response.status_code == 200


def test_trust_proxy_false_ignores_header():
    """When trust_proxy=False, X-Forwarded-For header is NOT used.

    Even if the header contains a whitelisted IP, the actual client host
    ('testclient', which is not a valid IP) is evaluated instead and blocked.
    """
    app = make_app(whitelist=["192.168.1.50"], trust_proxy=False)
    client = TestClient(app)
    # Header says whitelisted IP, but trust_proxy=False so it is ignored.
    # The real client host 'testclient' is not a valid IP → denied.
    response = client.get("/ping", headers={"X-Forwarded-For": "192.168.1.50"})
    assert response.status_code == 403


def test_invalid_whitelist_entry_ignored():
    """A non-IP string in the whitelist is silently skipped; valid entries still apply."""
    # "not-an-ip" should be logged as a warning and ignored.
    # The remaining valid entry "192.168.1.10" still applies.
    app = make_app(whitelist=["not-an-ip", "192.168.1.10"], trust_proxy=True)
    client = TestClient(app)
    # IP matching the valid entry → allowed
    response = client.get("/ping", headers={"X-Forwarded-For": "192.168.1.10"})
    assert response.status_code == 200
    # IP not matching → denied (middleware is still functional)
    response2 = client.get("/ping", headers={"X-Forwarded-For": "10.0.0.1"})
    assert response2.status_code == 403


def test_403_response_body():
    """Blocked response must contain 'error' and 'detail' keys."""
    app = make_app(whitelist=["10.0.0.1"], trust_proxy=True)
    client = TestClient(app)
    response = client.get("/ping", headers={"X-Forwarded-For": "9.9.9.9"})
    assert response.status_code == 403
    body = response.json()
    assert "error" in body
    assert "detail" in body
