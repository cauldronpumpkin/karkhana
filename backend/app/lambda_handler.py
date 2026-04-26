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
