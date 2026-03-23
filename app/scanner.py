from __future__ import annotations

from datetime import datetime, timezone

from app.models import BookSnapshot, SignalResult


def safe_float(x: str | float | int | None) -> float | None:
    if x is None:
        return None
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def top_of_book(book) -> tuple[float | None, float | None]:
    best_bid = safe_float(book.bids[0].price) if book.bids else None
    best_ask = safe_float(book.asks[0].price) if book.asks else None
    return best_bid, best_ask


def compute_mid(best_bid: float | None, best_ask: float | None) -> float | None:
    if best_bid is not None and best_ask is not None:
        return (best_bid + best_ask) / 2.0
    return best_bid if best_bid is not None else best_ask


def compute_spread(best_bid: float | None, best_ask: float | None) -> float | None:
    if best_bid is None or best_ask is None:
        return None
    return max(0.0, best_ask - best_bid)


def snapshot_from_market_and_book(market, token, book) -> BookSnapshot:
    best_bid, best_ask = top_of_book(book)
    mid = compute_mid(best_bid, best_ask)
    spread = compute_spread(best_bid, best_ask)

    return BookSnapshot(
        token_id=token.token_id,
        market_id=market.id,
        question=market.question,
        outcome=token.outcome,
        best_bid=best_bid,
        best_ask=best_ask,
        mid_price=mid,
        spread=spread,
        liquidity=market.liquidity,
        volume=market.volume,
        ts=datetime.now(timezone.utc),
    )


def score_snapshot(
    snap: BookSnapshot,
    price_5m_ago: float | None,
) -> SignalResult:
    flags: list[str] = []

    price_change_5m = None
    if snap.mid_price is not None and price_5m_ago is not None:
        price_change_5m = snap.mid_price - price_5m_ago

    score = 0.0

    if snap.spread is not None:
        score += min(snap.spread / 0.1, 1.0) * 2.0
        if snap.spread >= 0.04:
            flags.append("wide_spread")

    if price_change_5m is not None:
        score += min(abs(price_change_5m) / 0.1, 1.0) * 1.5
        if abs(price_change_5m) >= 0.05:
            flags.append("fast_move")

    if snap.liquidity is not None and snap.liquidity < 5000:
        score += 1.0
        flags.append("low_liquidity")

    if snap.mid_price is not None and (snap.mid_price < 0.05 or snap.mid_price > 0.95):
        flags.append("extreme_probability")

    return SignalResult(
        token_id=snap.token_id,
        market_id=snap.market_id,
        question=snap.question,
        outcome=snap.outcome,
        mid_price=snap.mid_price,
        spread=snap.spread,
        price_change_5m=price_change_5m,
        liquidity=snap.liquidity,
        volume=snap.volume,
        score=score,
        flags=flags,
    )
