from __future__ import annotations

from typing import Any

import httpx
from pydantic import TypeAdapter
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import settings
from app.models import Market, OrderBook


class PolymarketClient:
    def __init__(self) -> None:
        limits = httpx.Limits(
            max_connections=settings.max_connections,
            max_keepalive_connections=settings.max_keepalive_connections,
        )
        timeout = httpx.Timeout(settings.request_timeout_seconds)

        self._gamma = httpx.AsyncClient(
            base_url=settings.gamma_base_url,
            timeout=timeout,
            limits=limits,
            headers={"Accept": "application/json"},
        )
        self._clob = httpx.AsyncClient(
            base_url=settings.clob_base_url,
            timeout=timeout,
            limits=limits,
            headers={"Accept": "application/json"},
        )

        self._markets_adapter = TypeAdapter(list[Market])

    async def aclose(self) -> None:
        await self._gamma.aclose()
        await self._clob.aclose()

    async def __aenter__(self) -> "PolymarketClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.aclose()

    async def _get_json(
        self,
        client: httpx.AsyncClient,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> Any:
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(4),
            wait=wait_exponential(multiplier=0.5, min=0.5, max=8),
            retry=retry_if_exception_type(
                (
                    httpx.TimeoutException,
                    httpx.NetworkError,
                    httpx.RemoteProtocolError,
                    httpx.HTTPStatusError,
                )
            ),
            reraise=True,
        ):
            with attempt:
                resp = await client.get(path, params=params)
                resp.raise_for_status()
                return resp.json()

        raise RuntimeError("Unreachable retry state")

    async def list_markets(
        self,
        *,
        active: bool = True,
        closed: bool = False,
        limit: int = 10,
        offset: int = 0,
    ) -> list[Market]:
        data = await self._get_json(
            self._gamma,
            "/markets",
            params={
                "active": str(active).lower(),
                "closed": str(closed).lower(),
                "limit": limit,
                "offset": offset,
            },
        )
        return self._markets_adapter.validate_python(data)

    async def search_markets(
        self,
        *,
        query: str,
        limit: int = 10,
    ) -> list[Market]:
        data = await self._get_json(
            self._gamma,
            "/markets",
            params={
                "search": query,
                "limit": limit,
            },
        )
        return self._markets_adapter.validate_python(data)

    async def get_orderbook(self, token_id: str) -> OrderBook:
        # Public CLOB read endpoints require no auth.
        data = await self._get_json(
            self._clob,
            "/book",
            params={"token_id": token_id},
        )
        return OrderBook.model_validate(data)