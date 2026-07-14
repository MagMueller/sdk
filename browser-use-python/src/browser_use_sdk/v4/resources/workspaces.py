from __future__ import annotations

import asyncio
import mimetypes
from pathlib import Path
from typing import TYPE_CHECKING, Any

import httpx

from ..._core.http import AsyncHttpClient, SyncHttpClient
from ...generated.v4.models import (
    WorkspaceFileListResponse,
    WorkspaceFileUploadItem,
    WorkspaceFileUploadResponse,
    WorkspaceFileUploadResponseItem,
    WorkspaceInfo,
)

if TYPE_CHECKING:
    from uuid import UUID


def _guess_content_type(path: str) -> str:
    ct, _ = mimetypes.guess_type(path)
    return ct or "application/octet-stream"


def _read_upload_items(
    resolved: list[Path],
) -> tuple[list[bytes], list[WorkspaceFileUploadItem]]:
    """Read each file's bytes ONCE and derive its presign item from that buffer.

    Reading once (rather than stat-then-reread) avoids a TOCTOU where a file
    mutated between presign and PUT no longer matches the size-pinned URL.
    """
    buffers = [p.read_bytes() for p in resolved]
    items = [
        WorkspaceFileUploadItem(
            name=p.name,
            contentType=_guess_content_type(str(p)),
            size=len(buf),
        )
        for p, buf in zip(resolved, buffers)
    ]
    return buffers, items


def _check_presign_length(
    resp_files: list[WorkspaceFileUploadResponseItem],
    items: list[WorkspaceFileUploadItem],
) -> None:
    """Raise a descriptive error if the presign response is short an upload URL."""
    if len(resp_files) < len(items):
        missing = ", ".join(
            f"{it.name} (position {len(resp_files) + i})"
            for i, it in enumerate(items[len(resp_files) :])
        )
        raise ValueError(
            f"Presign response has {len(resp_files)} upload URL(s) but "
            f"{len(items)} file(s) were requested. Missing upload URL for: {missing}"
        )


class Workspaces:
    def __init__(self, http: SyncHttpClient) -> None:
        self._http = http

    def create(
        self,
        *,
        name: str | None = None,
        **extra: Any,
    ) -> WorkspaceInfo:
        """Create a new workspace."""
        body: dict[str, Any] = {}
        if name is not None:
            body["name"] = name
        body.update(extra)
        return WorkspaceInfo.model_validate(
            self._http.request("POST", "/workspaces", json=body)
        )

    def get(self, workspace_id: str | UUID) -> WorkspaceInfo:
        """Get workspace details."""
        return WorkspaceInfo.model_validate(
            self._http.request("GET", f"/workspaces/{workspace_id}")
        )

    def files(
        self,
        workspace_id: str | UUID,
        *,
        prefix: str | None = None,
        limit: int | None = None,
        cursor: str | None = None,
        include_urls: bool | None = None,
        content_disposition: str | None = None,
    ) -> WorkspaceFileListResponse:
        """List files in a workspace with cursor-based pagination."""
        return WorkspaceFileListResponse.model_validate(
            self._http.request(
                "GET",
                f"/workspaces/{workspace_id}/files",
                params={
                    "prefix": prefix,
                    "limit": limit,
                    "cursor": cursor,
                    "includeUrls": include_urls,
                    "contentDisposition": content_disposition,
                },
            )
        )

    def upload_files(
        self,
        workspace_id: str | UUID,
        files: list[WorkspaceFileUploadItem],
        **extra: Any,
    ) -> WorkspaceFileUploadResponse:
        """Get presigned PUT URLs for workspace file uploads."""
        body: dict[str, Any] = {
            "files": [f.model_dump(by_alias=True, exclude_none=True) for f in files],
        }
        body.update(extra)
        return WorkspaceFileUploadResponse.model_validate(
            self._http.request(
                "POST",
                f"/workspaces/{workspace_id}/files/upload",
                json=body,
            )
        )

    def upload(
        self,
        workspace_id: str | UUID,
        *paths: str | Path,
    ) -> list[WorkspaceFileUploadResponseItem]:
        """Upload local files to a workspace: presign + PUT in one call.

        Returns the upload items — pass their ``id``s as ``attached_file_ids``
        in ``runs.create()`` to attach the files to a run.

        Usage::

            uploaded = client.workspaces.upload(ws_id, "data.csv")
            client.runs.create("...", workspace_id=ws_id, attached_file_ids=[f.id for f in uploaded])
        """
        resolved = [Path(p) for p in paths]
        buffers, items = _read_upload_items(resolved)
        resp = self.upload_files(workspace_id, items)
        _check_presign_length(resp.files, items)
        with httpx.Client(timeout=60) as http:
            for buf, item, resp_item in zip(buffers, items, resp.files):
                http.put(
                    resp_item.upload_url,
                    content=buf,
                    headers={"Content-Type": item.content_type or "application/octet-stream"},
                ).raise_for_status()
        return list(resp.files)


class AsyncWorkspaces:
    def __init__(self, http: AsyncHttpClient) -> None:
        self._http = http

    async def create(
        self,
        *,
        name: str | None = None,
        **extra: Any,
    ) -> WorkspaceInfo:
        """Create a new workspace."""
        body: dict[str, Any] = {}
        if name is not None:
            body["name"] = name
        body.update(extra)
        return WorkspaceInfo.model_validate(
            await self._http.request("POST", "/workspaces", json=body)
        )

    async def get(self, workspace_id: str | UUID) -> WorkspaceInfo:
        """Get workspace details."""
        return WorkspaceInfo.model_validate(
            await self._http.request("GET", f"/workspaces/{workspace_id}")
        )

    async def files(
        self,
        workspace_id: str | UUID,
        *,
        prefix: str | None = None,
        limit: int | None = None,
        cursor: str | None = None,
        include_urls: bool | None = None,
        content_disposition: str | None = None,
    ) -> WorkspaceFileListResponse:
        """List files in a workspace with cursor-based pagination."""
        return WorkspaceFileListResponse.model_validate(
            await self._http.request(
                "GET",
                f"/workspaces/{workspace_id}/files",
                params={
                    "prefix": prefix,
                    "limit": limit,
                    "cursor": cursor,
                    "includeUrls": include_urls,
                    "contentDisposition": content_disposition,
                },
            )
        )

    async def upload_files(
        self,
        workspace_id: str | UUID,
        files: list[WorkspaceFileUploadItem],
        **extra: Any,
    ) -> WorkspaceFileUploadResponse:
        """Get presigned PUT URLs for workspace file uploads."""
        body: dict[str, Any] = {
            "files": [f.model_dump(by_alias=True, exclude_none=True) for f in files],
        }
        body.update(extra)
        return WorkspaceFileUploadResponse.model_validate(
            await self._http.request(
                "POST",
                f"/workspaces/{workspace_id}/files/upload",
                json=body,
            )
        )

    async def upload(
        self,
        workspace_id: str | UUID,
        *paths: str | Path,
    ) -> list[WorkspaceFileUploadResponseItem]:
        """Upload local files to a workspace: presign + PUT in one call.

        Returns the upload items — pass their ``id``s as ``attached_file_ids``
        in ``runs.create()`` to attach the files to a run.

        Usage::

            uploaded = await client.workspaces.upload(ws_id, "data.csv")
        """
        resolved = [Path(p) for p in paths]
        # Offload blocking disk reads to a thread so we don't stall the event
        # loop (and starve other coroutines) on large files.
        buffers, items = await asyncio.to_thread(_read_upload_items, resolved)
        resp = await self.upload_files(workspace_id, items)
        _check_presign_length(resp.files, items)
        async with httpx.AsyncClient(timeout=60) as http:
            for buf, item, resp_item in zip(buffers, items, resp.files):
                r = await http.put(
                    resp_item.upload_url,
                    content=buf,
                    headers={"Content-Type": item.content_type or "application/octet-stream"},
                )
                r.raise_for_status()
        return list(resp.files)
