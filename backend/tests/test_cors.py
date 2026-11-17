"""Tests for CORS origin resolution and middleware rules."""

from starlette.middleware.cors import CORSMiddleware
from starlette.types import ASGIApp
from app.config import settings
from app.main import get_allowed_origins


def test_get_allowed_origins_wildcard():
    """Verify default wildcard setting allows any origin."""
    origins = get_allowed_origins()
    assert origins == ["*"]


def test_get_allowed_origins_custom_list(monkeypatch):
    """Verify custom origins are parsed and local development hosts are included."""
    monkeypatch.setattr(
        settings,
        "ALLOWED_ORIGINS",
        "https://ai-job-agent.vercel.app, https://job-agent.onrender.com",
    )
    origins = get_allowed_origins()
    assert "https://ai-job-agent.vercel.app" in origins
    assert "https://job-agent.onrender.com" in origins
    assert "http://localhost:5173" in origins

#dsfmdshablkfh

def test_cors_middleware_allowed_origin_matching():
    """Verify that CORSMiddleware correctly recognizes allowed origins."""
    dummy_app: ASGIApp = lambda scope, receive, send: None
    middleware = CORSMiddleware(
        app=dummy_app,
        allow_origins=get_allowed_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    assert middleware.is_allowed_origin("https://any-frontend.vercel.app") is True
    assert middleware.is_allowed_origin("http://localhost:5173") is True
