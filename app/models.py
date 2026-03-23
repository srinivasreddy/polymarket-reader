from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator
from datetime import datetime


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
    clobTokenIds: str | None = None
    outcomes: str | None = None
    outcomePrices: str | None = None

    model_config = ConfigDict(extra="allow")

    @model_validator(mode="after")
    def build_tokens_from_clob_fields(self) -> "Market":
        if self.tokens:
            return self
        if not self.clobTokenIds:
            return self
        try:
            token_ids: list[str] = json.loads(self.clobTokenIds)
            outcome_names: list[str] = (
                json.loads(self.outcomes) if self.outcomes else []
            )
            outcome_prices: list[str] = (
                json.loads(self.outcomePrices) if self.outcomePrices else []
            )
            self.tokens = [
                Token(
                    token_id=tid,
                    outcome=outcome_names[i] if i < len(outcome_names) else None,
                    price=float(outcome_prices[i]) if i < len(outcome_prices) else None,
                )
                for i, tid in enumerate(token_ids)
            ]
        except Exception:
            pass
        return self


class OrderBookLevel(BaseModel):
    price: str
    size: str


class OrderBook(BaseModel):
    market: str | None = None
    asset_id: str | None = None
    bids: list[OrderBookLevel] = []
    asks: list[OrderBookLevel] = []

    model_config = ConfigDict(extra="allow")


class BookSnapshot(BaseModel):
    token_id: str
    market_id: str | None = None
    question: str | None = None
    outcome: str | None = None

    gamma_price: float | None = None  # Gamma API reference price (outcomePrices)
    best_bid: float | None = None
    best_ask: float | None = None
    bid_size: float | None = None  # Contract size at best bid
    ask_size: float | None = None  # Contract size at best ask
    bid_depth: float | None = None  # Dollar value at best bid (price * size)
    ask_depth: float | None = None  # Dollar value at best ask (price * size)
    mid_price: float | None = None
    spread: float | None = None

    liquidity: float | None = None
    volume: float | None = None

    ts: datetime

    model_config = ConfigDict(extra="allow")


class SignalResult(BaseModel):
    token_id: str
    market_id: str | None = None
    question: str | None = None
    outcome: str | None = None

    mid_price: float | None = None
    spread: float | None = None
    price_change_5m: float | None = None
    gamma_divergence: float | None = None  # |mid - gamma_price|
    arb_gap: float | None = None  # 1 - complement_ask_sum (>0 = buy arb)
    bid_depth: float | None = None
    ask_depth: float | None = None
    liquidity: float | None = None
    volume: float | None = None

    score: float
    flags: list[str]

    model_config = ConfigDict(extra="allow")
