from __future__ import annotations

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
        items = [
            WorkspaceFileUploadItem(
                name=p.name,
                contentType=_guess_content_type(str(p)),
                size=p.stat().st_size,
            )
            for p in resolved
        ]
        resp = self.upload_files(workspace_id, items)
        with httpx.Client(timeout=60) as http:
            for p, item in zip(resolved, resp.files):
                http.put(
                    item.upload_url,
                    content=p.read_bytes(),
                    headers={"Content-Type": _guess_content_type(str(p))},
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
        items = [
            WorkspaceFileUploadItem(
                name=p.name,
                contentType=_guess_content_type(str(p)),
                size=p.stat().st_size,
            )
            for p in resolved
        ]
        resp = await self.upload_files(workspace_id, items)
        async with httpx.AsyncClient(timeout=60) as http:
            for p, item in zip(resolved, resp.files):
                r = await http.put(
                    item.upload_url,
                    content=p.read_bytes(),
                    headers={"Content-Type": _guess_content_type(str(p))},
                )
                r.raise_for_status()
        return list(resp.files)
