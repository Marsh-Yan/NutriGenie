"""Unexpected exceptions must not disclose connection strings or secrets."""

from fastapi.testclient import TestClient

from app.main import app


def test_unhandled_error_response_is_sanitized():
    @app.get("/__test_phase_f_error")
    def raise_private_error():
        raise RuntimeError("mysql+pymysql://demo:private-password@localhost/nutrigenie")

    try:
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/__test_phase_f_error")
        assert response.status_code == 500
        assert response.json() == {"detail": "服务器内部错误，请稍后重试"}
        assert "private-password" not in response.text
    finally:
        app.router.routes = [route for route in app.router.routes if getattr(route, "path", None) != "/__test_phase_f_error"]
