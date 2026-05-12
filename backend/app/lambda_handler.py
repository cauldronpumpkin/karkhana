"""
DEPRECATED — Single-Server Migration.

The FastAPI backend now runs as a standalone Uvicorn server on :8000.
Lambda via API Gateway (Mangum handler) is retained only for historical
reference and eventual retirement inventory. The supported runtime path
is ``uvicorn backend.app.main:app`` with Floci for local AWS emulation.

See: docs/local-first-floci.md, docs/aws-retirement.md
"""

import asyncio

from mangum import Mangum

from backend.app.main import app
from backend.app.services.local_workers import LocalWorkerService

api_handler = Mangum(app, lifespan="off")


def handler(event, context):
    records = event.get("Records") if isinstance(event, dict) else None
    if records and all(record.get("eventSource") == "aws:sqs" for record in records):
        return asyncio.run(LocalWorkerService().process_sqs_records(records))
    return api_handler(event, context)
