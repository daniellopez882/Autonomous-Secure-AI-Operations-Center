"""
API and WebSocket behaviour.

The service previously had no tests at all. These cover the probes, the policy
endpoint, and the WebSocket auth gate, plus the property that the app starts
without the AWS SDK -- it used to import boto3 at module scope to serve a
simulation that never calls AWS.
"""

from __future__ import annotations

import pytest


class TestProbes:
    def test_health_is_live(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "healthy"

    def test_health_reports_connection_count(self, client):
        assert client.get("/health").json()["active_connections"] == 0

    def test_ready_reports_each_check(self, client):
        checks = client.get("/ready").json()["checks"]
        assert set(checks) == {"telemetry_task", "guardrails", "ws_auth_configured"}

    def test_ready_confirms_the_telemetry_task_is_running(self, client):
        """The old background task could die silently and nothing would notice."""
        assert client.get("/ready").json()["checks"]["telemetry_task"]["ok"] is True

    def test_ready_self_tests_the_guardrail(self, client):
        assert client.get("/ready").json()["checks"]["guardrails"]["ok"] is True


class TestPolicyEndpoint:
    @pytest.mark.parametrize(
        "action,expected",
        [
            ("LOG_QUERY", "allow"),
            ("ALERT_CREATE", "allow"),
            ("IAM_REVOKE", "require_approval"),
            ("K8S_ISOLATE", "require_approval"),
            ("BLOCK_IP", "require_approval"),
        ],
    )
    def test_decisions(self, client, action, expected):
        r = client.get("/api/v1/policy/evaluate", params={"action_type": action})
        assert r.status_code == 200
        assert r.json()["decision"] == expected

    def test_destructive_and_irreversible_in_production_is_denied(self, client):
        r = client.get(
            "/api/v1/policy/evaluate",
            params={"action_type": "K8S_TERMINATE", "production": True, "irreversible": True},
        )
        assert r.json()["decision"] == "deny"

    def test_response_carries_reasons(self, client):
        body = client.get("/api/v1/policy/evaluate", params={"action_type": "IAM_REVOKE"}).json()
        assert body["reasons"]
        assert body["risk_level"] in {"low", "medium", "high", "critical"}

    def test_alias_is_resolved_in_the_response(self, client):
        body = client.get("/api/v1/policy/evaluate", params={"action_type": "BLOCK_IP"}).json()
        assert body["action_type"] == "NETWORK_BLOCK"

    def test_overlong_action_type_is_rejected(self, client):
        r = client.get("/api/v1/policy/evaluate", params={"action_type": "X" * 200})
        assert r.status_code == 422

    def test_missing_action_type_is_rejected(self, client):
        assert client.get("/api/v1/policy/evaluate").status_code == 422


class TestWebSocketAuth:
    def test_connects_without_a_token_outside_production(self, client):
        with client.websocket_connect("/ws/threat-feed") as ws:
            ws.send_text("APPROVE_ACTION")
            assert ws.receive_json()["agent"] == "System"

    def test_token_is_required_when_configured(self, client, monkeypatch):
        from core.config.settings import settings

        monkeypatch.setattr(settings, "WS_AUTH_TOKEN", "s3cret")
        with pytest.raises(Exception):
            with client.websocket_connect("/ws/threat-feed"):
                pass

    def test_correct_token_is_accepted(self, client, monkeypatch):
        from core.config.settings import settings

        monkeypatch.setattr(settings, "WS_AUTH_TOKEN", "s3cret")
        with client.websocket_connect("/ws/threat-feed?token=s3cret") as ws:
            ws.send_text("APPROVE_ACTION")
            assert ws.receive_json()["status"] == "approved"

    def test_wrong_token_is_rejected(self, client, monkeypatch):
        from core.config.settings import settings

        monkeypatch.setattr(settings, "WS_AUTH_TOKEN", "s3cret")
        with pytest.raises(Exception):
            with client.websocket_connect("/ws/threat-feed?token=wrong"):
                pass


class TestNoHeavyImports:
    def test_app_imports_without_the_aws_sdk(self):
        """
        api.py used to import the agent modules at module scope, which import
        boto3, so the simulation could not start without the AWS SDK.
        """
        import api

        assert api.app is not None

    def test_agent_modules_are_not_imported_at_startup(self):
        import importlib
        import sys

        for mod in list(sys.modules):
            if mod.startswith("agents."):
                del sys.modules[mod]
        importlib.reload(importlib.import_module("api"))
        assert not [m for m in sys.modules if m.startswith("agents.")], (
            "importing api pulled in agent modules, which drag in boto3"
        )


class TestLoggingConfiguration:
    """
    Module-level get_logger() calls configure logging at import time. Because
    setup_logging is idempotent, the lifespan handler's call was a no-op and
    JSON_LOGS / LOG_LEVEL from the environment were silently ignored -- the
    container ran with JSON_LOGS=true and still emitted plain text.
    """

    def test_lifespan_applies_the_configured_format(self, monkeypatch):
        import logging

        from core.config.settings import settings
        from core.logging_config import JsonFormatter

        monkeypatch.setattr(settings, "JSON_LOGS", True)

        from fastapi.testclient import TestClient

        from api import app

        with TestClient(app):
            handlers = logging.getLogger().handlers
            assert handlers, "root logger has no handler"
            assert isinstance(handlers[0].formatter, JsonFormatter), (
                "JSON_LOGS=true did not take effect; setup_logging was a no-op"
            )
