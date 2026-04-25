"""Umumiy pytest fixturalari."""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_session
from app.main import app


@pytest.fixture
def client():
    """Mocked session bilan TestClient."""

    def _override():
        yield MagicMock()

    app.dependency_overrides[get_session] = _override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
