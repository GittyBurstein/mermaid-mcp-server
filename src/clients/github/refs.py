from __future__ import annotations
from typing import Awaitable, Callable, Mapping, Optional, Any
import httpx
from core.errors import NotFoundError

RequestFn = Callable[[httpx.AsyncClient, str], Awaitable[httpx.Response]]

async def fetch_tree_sha(
    request: RequestFn,
    client: httpx.AsyncClient,
    *,
    owner: str,
    repo: str,
    ref: str,
) -> Optional[str]:
    # Use commits API so we can reliably read commit.tree.sha
    resp = await request(client, f"/repos/{owner}/{repo}/commits/{ref}")
    if resp.status_code in (404, 422):
        return None
    resp.raise_for_status()
    data = resp.json()
    return str(data["commit"]["tree"]["sha"])

async def resolve_tree_sha(
    request: RequestFn,
    client: httpx.AsyncClient,
    *,
    owner: str,
    repo: str,
    ref: str,
) -> str:
    sha = await fetch_tree_sha(request, client, owner=owner, repo=repo, ref=ref)
    if sha:
        return sha

    repo_resp = await request(client, f"/repos/{owner}/{repo}")
    if repo_resp.status_code == 404:
        raise NotFoundError(f"Repository not found: {owner}/{repo}")
    repo_resp.raise_for_status()

    default_branch = (repo_resp.json() or {}).get("default_branch") or "main"
    default_branch = str(default_branch).strip() or "main"

    sha2 = await fetch_tree_sha(request, client, owner=owner, repo=repo, ref=default_branch)
    if sha2:
        return sha2

    raise NotFoundError(f"Unable to resolve reference: {ref}")
