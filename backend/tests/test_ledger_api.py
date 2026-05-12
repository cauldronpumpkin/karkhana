"""Tests for the Factory Run Ledger REST API."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.factory_run_ledger import FactoryRunLedgerError

client = TestClient(app)

LEDGER_ID = "abc123def456"


@pytest.fixture
def mock_dynamo():
    """Mock DynamoDBLedgerService to avoid real AWS calls."""
    with patch("backend.app.routers.ledger.get_dynamo_service") as mock_get:
        svc = MagicMock()
        mock_get.return_value = svc
        yield svc


def _make_record(ledger_id: str = LEDGER_ID, **overrides):
    return {
        "ledger_id": ledger_id,
        "run_id": "test-run",
        "title": "Test Ledger",
        "status": "active",
        "stage": "planning",
        "created_at": "2026-05-01T00:00:00Z",
        "updated_at": "2026-05-01T00:00:00Z",
        "s3_key": "",
        "entity": "FactoryRunLedger",
        "PK": f"LEDGER#{ledger_id}",
        "SK": "METADATA",
        **overrides,
    }


# ---------------------------------------------------------------------------
# GET /api/ledgers/{run_id} — list
# ---------------------------------------------------------------------------

def test_list_ledgers_empty(mock_dynamo):
    mock_dynamo.list_ledgers_for_run.return_value = []
    response = client.get("/api/ledgers/test-run")
    assert response.status_code == 200
    assert response.json() == {"ledgers": []}


def test_list_ledgers_with_records(mock_dynamo):
    mock_dynamo.list_ledgers_for_run.return_value = [
        _make_record(LEDGER_ID),
        _make_record("def456abc789", title="Second Ledger"),
    ]
    response = client.get("/api/ledgers/test-run")
    assert response.status_code == 200
    data = response.json()
    assert len(data["ledgers"]) == 2
    assert data["ledgers"][0]["title"] == "Test Ledger"
    assert data["ledgers"][1]["title"] == "Second Ledger"


def test_list_ledgers_dynamo_error(mock_dynamo):
    mock_dynamo.list_ledgers_for_run.side_effect = FactoryRunLedgerError("Not found")
    response = client.get("/api/ledgers/test-run")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/ledgers/{run_id}/{ledger_id} — single
# ---------------------------------------------------------------------------

def test_get_ledger_success(mock_dynamo):
    mock_dynamo.get_ledger_record.return_value = _make_record(s3_key="ledgers/test-run/abc.md")
    with patch("backend.app.routers.ledger.get_ledger_body") as mock_body:
        mock_body.return_value = "# Test body"
        response = client.get(f"/api/ledgers/test-run/{LEDGER_ID}")
    assert response.status_code == 200
    data = response.json()
    assert data["ledger_id"] == LEDGER_ID
    assert data["title"] == "Test Ledger"
    assert data["body"] == "# Test body"


def test_get_ledger_not_found(mock_dynamo):
    mock_dynamo.get_ledger_record.side_effect = FactoryRunLedgerError("Not found")
    response = client.get(f"/api/ledgers/test-run/{LEDGER_ID}")
    assert response.status_code == 404


def test_get_ledger_wrong_run(mock_dynamo):
    mock_dynamo.get_ledger_record.return_value = _make_record(run_id="other-run")
    response = client.get(f"/api/ledgers/test-run/{LEDGER_ID}")
    assert response.status_code == 404


def test_get_ledger_s3_failure_returns_empty_body(mock_dynamo):
    mock_dynamo.get_ledger_record.return_value = _make_record(s3_key="ledgers/test-run/abc.md")
    with patch("backend.app.routers.ledger.get_ledger_body", side_effect=Exception("S3 down")):
        response = client.get(f"/api/ledgers/test-run/{LEDGER_ID}")
    assert response.status_code == 200
    assert response.json()["body"] == ""


# ---------------------------------------------------------------------------
# POST /api/ledgers/{run_id} — create
# ---------------------------------------------------------------------------

def test_create_ledger_minimal(mock_dynamo):
    mock_dynamo.create_ledger_record.return_value = LEDGER_ID
    mock_dynamo.get_ledger_record.return_value = _make_record()
    with patch("backend.app.routers.ledger.store_ledger_body") as mock_s3:
        response = client.post(
            "/api/ledgers/test-run",
            json={"title": "New Ledger"},
        )
    assert response.status_code == 201
    data = response.json()
    assert data["ledger_id"] == LEDGER_ID
    assert data["title"] == "Test Ledger"
    # No body, so S3 should not be called
    mock_s3.assert_not_called()


def test_create_ledger_with_body(mock_dynamo):
    mock_dynamo.create_ledger_record.return_value = LEDGER_ID
    mock_dynamo.get_ledger_record.return_value = _make_record(s3_key="ledgers/test-run/abc123.md")
    with patch("backend.app.routers.ledger.store_ledger_body") as mock_s3:
        mock_s3.return_value = "ledgers/test-run/abc123.md"
        response = client.post(
            "/api/ledgers/test-run",
            json={"title": "Rich Ledger", "body": "# My body", "status": "active", "stage": "development"},
        )
    assert response.status_code == 201
    mock_s3.assert_called_once_with(LEDGER_ID, "test-run", "# My body")


def test_create_ledger_missing_title(mock_dynamo):
    response = client.post(
        "/api/ledgers/test-run",
        json={"status": "active"},
    )
    assert response.status_code == 422  # Validation error


# ---------------------------------------------------------------------------
# PATCH /api/ledgers/{run_id}/{ledger_id} — update
# ---------------------------------------------------------------------------

def test_update_ledger_title(mock_dynamo):
    mock_dynamo.get_ledger_record.return_value = _make_record()
    mock_dynamo.update_ledger_record.return_value = _make_record(title="Updated Title")
    response = client.patch(
        f"/api/ledgers/test-run/{LEDGER_ID}",
        json={"title": "Updated Title"},
    )
    assert response.status_code == 200
    mock_dynamo.update_ledger_record.assert_called_once_with(LEDGER_ID, {"title": "Updated Title"})


def test_update_ledger_status_and_stage(mock_dynamo):
    mock_dynamo.get_ledger_record.return_value = _make_record()
    mock_dynamo.update_ledger_record.return_value = _make_record(status="completed", stage="done")
    response = client.patch(
        f"/api/ledgers/test-run/{LEDGER_ID}",
        json={"status": "completed", "stage": "done"},
    )
    assert response.status_code == 200
    mock_dynamo.update_ledger_record.assert_called_once_with(
        LEDGER_ID, {"status": "completed", "stage": "done"}
    )


def test_update_ledger_body(mock_dynamo):
    mock_dynamo.get_ledger_record.return_value = _make_record()
    mock_dynamo.update_ledger_record.return_value = _make_record(s3_key="ledgers/test-run/abc.md")
    with patch("backend.app.routers.ledger.store_ledger_body") as mock_s3:
        mock_s3.return_value = "ledgers/test-run/abc.md"
        response = client.patch(
            f"/api/ledgers/test-run/{LEDGER_ID}",
            json={"body": "# New body"},
        )
    assert response.status_code == 200
    mock_s3.assert_called_once_with(LEDGER_ID, "test-run", "# New body")


def test_update_ledger_not_found(mock_dynamo):
    mock_dynamo.get_ledger_record.side_effect = FactoryRunLedgerError("Not found")
    response = client.patch(
        f"/api/ledgers/test-run/{LEDGER_ID}",
        json={"title": "Nope"},
    )
    assert response.status_code == 404


def test_update_ledger_wrong_run(mock_dynamo):
    mock_dynamo.get_ledger_record.return_value = _make_record(run_id="other-run")
    response = client.patch(
        f"/api/ledgers/test-run/{LEDGER_ID}",
        json={"title": "Nope"},
    )
    assert response.status_code == 404
