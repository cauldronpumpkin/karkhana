from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_amplify_preview_origin_is_allowed_by_cors(test_client):
    response = await test_client.options(
        "/api/health",
        headers={
            "Origin": "https://main.dgwcq4220e760.amplifyapp.com",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://main.dgwcq4220e760.amplifyapp.com"
