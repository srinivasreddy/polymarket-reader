from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Token(BaseModel):
    token_id: str | None = Field(default=None, alias="token_id")
    outcome: str | None = None
    price: float | None = None

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class Market(BaseModel):
    id: str | None = None
    question: str | None = None
    active: bool | None = None
    closed: bool | None = None
    end_date: str | None = None
    liquidity: float | None = None
    volume: float | None = None
    slug: str | None = None
    tags: list[Any] | None = None
    tokens: list[Token] | None = None

    model_config = ConfigDict(extra="allow")


class OrderBookLevel(BaseModel):
    price: str
    size: str


class OrderBook(BaseModel):
    market: str | None = None
    asset_id: str | None = None
    bids: list[OrderBookLevel] = []
    asks: list[OrderBookLevel] = []

    model_config = ConfigDict(extra="allow")
