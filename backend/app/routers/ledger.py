"""Factory Run Ledger REST API endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.app.services.factory_run_ledger import (
    DynamoDBLedgerService,
    FactoryRunLedgerError,
    get_ledger_body,
    store_ledger_body,
)

router = APIRouter(prefix="/api/ledgers", tags=["ledgers"])

_dynamo_service: DynamoDBLedgerService | None = None


def get_dynamo_service() -> DynamoDBLedgerService:
    global _dynamo_service
    if _dynamo_service is None:
        _dynamo_service = DynamoDBLedgerService()
    return _dynamo_service


class CreateLedgerRequest(BaseModel):
    title: str = Field(..., min_length=1)
    status: str = Field(default="active")
    stage: str = Field(default="planning")
    body: str = Field(default="")


class UpdateLedgerRequest(BaseModel):
    title: str | None = None
    status: str | None = None
    stage: str | None = None
    body: str | None = None


@router.get("/{run_id}")
async def list_ledgers(run_id: str):
    """List all ledger records for a factory run."""
    try:
        records = get_dynamo_service().list_ledgers_for_run(run_id)
        summaries = []
        for rec in records:
            summaries.append({
                "ledger_id": rec.get("ledger_id"),
                "run_id": rec.get("run_id"),
                "title": rec.get("title"),
                "status": rec.get("status"),
                "stage": rec.get("stage"),
                "created_at": rec.get("created_at"),
                "updated_at": rec.get("updated_at"),
                "s3_key": rec.get("s3_key"),
            })
        return {"ledgers": summaries}
    except FactoryRunLedgerError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/{run_id}/{ledger_id}")
async def get_ledger(run_id: str, ledger_id: str):
    """Get a single ledger record with markdown body from S3."""
    try:
        record = get_dynamo_service().get_ledger_record(ledger_id)
        if record.get("run_id") != run_id:
            raise HTTPException(status_code=404, detail="Ledger not found for this run")

        body = ""
        s3_key = record.get("s3_key")
        if s3_key:
            try:
                body = get_ledger_body(ledger_id, run_id)
            except Exception:
                body = ""

        return {
            "ledger_id": record.get("ledger_id"),
            "run_id": record.get("run_id"),
            "title": record.get("title"),
            "status": record.get("status"),
            "stage": record.get("stage"),
            "created_at": record.get("created_at"),
            "updated_at": record.get("updated_at"),
            "s3_key": record.get("s3_key"),
            "body": body,
        }
    except FactoryRunLedgerError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/{run_id}", status_code=201)
async def create_ledger(run_id: str, body: CreateLedgerRequest):
    """Create a new ledger entry for a factory run."""
    try:
        ledger_id = get_dynamo_service().create_ledger_record(
            run_id=run_id,
            title=body.title,
            status=body.status,
            stage=body.stage,
        )
        s3_key = ""
        if body.body:
            s3_key = store_ledger_body(ledger_id, run_id, body.body)
            get_dynamo_service().update_ledger_record(ledger_id, {"s3_key": s3_key})

        record = get_dynamo_service().get_ledger_record(ledger_id)
        return {
            "ledger_id": record.get("ledger_id"),
            "run_id": record.get("run_id"),
            "title": record.get("title"),
            "status": record.get("status"),
            "stage": record.get("stage"),
            "created_at": record.get("created_at"),
            "updated_at": record.get("updated_at"),
            "s3_key": record.get("s3_key"),
        }
    except FactoryRunLedgerError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.patch("/{run_id}/{ledger_id}")
async def update_ledger(run_id: str, ledger_id: str, body: UpdateLedgerRequest):
    """Update an existing ledger entry."""
    try:
        record = get_dynamo_service().get_ledger_record(ledger_id)
        if record.get("run_id") != run_id:
            raise HTTPException(status_code=404, detail="Ledger not found for this run")

        updates: dict[str, str] = {}
        if body.title is not None:
            updates["title"] = body.title
        if body.status is not None:
            updates["status"] = body.status
        if body.stage is not None:
            updates["stage"] = body.stage

        if updates:
            record = get_dynamo_service().update_ledger_record(ledger_id, updates)

        s3_key = record.get("s3_key", "")
        if body.body is not None:
            if body.body:
                s3_key = store_ledger_body(ledger_id, run_id, body.body)
            else:
                s3_key = ""
            record = get_dynamo_service().update_ledger_record(ledger_id, {"s3_key": s3_key})

        return {
            "ledger_id": record.get("ledger_id"),
            "run_id": record.get("run_id"),
            "title": record.get("title"),
            "status": record.get("status"),
            "stage": record.get("stage"),
            "created_at": record.get("created_at"),
            "updated_at": record.get("updated_at"),
            "s3_key": record.get("s3_key"),
        }
    except FactoryRunLedgerError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
