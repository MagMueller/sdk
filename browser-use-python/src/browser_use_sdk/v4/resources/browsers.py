from __future__ import annotations

from typing import TYPE_CHECKING

from ..._core.http import AsyncHttpClient, SyncHttpClient
from ...generated.v4.models import BrowserSessionView

if TYPE_CHECKING:
    from uuid import UUID


class Browsers:
    def __init__(self, http: SyncHttpClient) -> None:
        self._http = http

    def stop(self, session_id: str | UUID) -> BrowserSessionView:
        """Stop a browser session and refund its unused time."""
        return BrowserSessionView.model_validate(
            self._http.request(
                "PATCH", f"/browsers/{session_id}", json={"action": "stop"}
            )
        )


class AsyncBrowsers:
    def __init__(self, http: AsyncHttpClient) -> None:
        self._http = http

    async def stop(self, session_id: str | UUID) -> BrowserSessionView:
        """Stop a browser session and refund its unused time."""
        return BrowserSessionView.model_validate(
            await self._http.request(
                "PATCH", f"/browsers/{session_id}", json={"action": "stop"}
            )
        )
