from __future__ import annotations

import json
from typing import Any

from backend.app.config import settings


class WorkerSqsPublisher:
    def __init__(self) -> None:
        self.queue_url = settings.worker_command_queue_url
        self.region = settings.worker_sqs_region

    def is_configured(self) -> bool:
        return bool(self.queue_url)

    async def send_job_available(self, item: Any, project: Any) -> None:
        if not self.is_configured():
            return
        envelope = {
            "type": "job_available",
            "work_item_id": item.id,
            "project_id": item.project_id,
            "idea_id": item.idea_id,
            "job_type": item.job_type,
            "payload": item.payload,
            "project": {
                "id": project.id,
                "repo_full_name": project.repo_full_name,
                "clone_url": project.clone_url,
                "default_branch": project.default_branch,
            },
        }
        self._client().send_message(
            QueueUrl=self.queue_url,
            MessageBody=json.dumps(envelope),
            MessageGroupId=f"project:{item.project_id}",
            MessageDeduplicationId=f"job:{item.id}:{item.updated_at.isoformat()}",
        )

    def _client(self):
        import boto3

        return boto3.client("sqs", region_name=self.region)
