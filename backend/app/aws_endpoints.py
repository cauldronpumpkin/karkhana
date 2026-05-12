from __future__ import annotations

import os


def endpoint_url(service: str) -> str | None:
    service_key = service.upper().replace("-", "_")
    return os.getenv(f"AWS_ENDPOINT_URL_{service_key}") or os.getenv("AWS_ENDPOINT_URL")
