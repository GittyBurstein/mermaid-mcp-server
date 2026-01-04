from __future__ import annotations

import httpx

from core.errors import ExternalServiceError, ValidationError


class KrokiClient:
    def __init__(self, *, base_url: str, timeout: float, verify: bool = False) -> None:
        self._base_url = (base_url or "").rstrip("/")
        self._timeout = timeout
        self._verify = verify

    async def render_mermaid_png(self, mermaid: str) -> bytes:
        code = (mermaid or "").strip()
        if not code:
            raise ValidationError("Mermaid code is empty")

        url = f"{self._base_url}/mermaid/png"

        try:
            async with httpx.AsyncClient(timeout=self._timeout, verify=self._verify) as c:
                r = await c.post(
                    url,
                    content=code.encode("utf-8"),
                    headers={"Content-Type": "text/plain; charset=utf-8"},
                )
                r.raise_for_status()
                return r.content
        except httpx.HTTPStatusError as e:
            raise ExternalServiceError(f"Kroki returned an error: {e}") from e
        except httpx.HTTPError as e:
            raise ExternalServiceError(f"Failed to call Kroki: {e}") from e
