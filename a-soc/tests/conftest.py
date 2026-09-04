"""Shared fixtures. Configuration is explicit so results do not depend on a
developer's local .env."""

from __future__ import annotations

import os

os.environ.setdefault("ENVIRONMENT", "testing")
os.environ.setdefault("LOG_LEVEL", "WARNING")
os.environ.setdefault("SIMULATION_STEP_SECONDS", "0")

import pytest


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from api import app

    with TestClient(app) as c:
        yield c
