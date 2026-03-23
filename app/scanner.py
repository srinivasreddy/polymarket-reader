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


def top_of_book(book) -> tuple[float | None, float | None, float | None, float | None]:
    # Bids are sorted ascending (lowest first), asks descending (highest first).
    # Best bid is the last bid; best ask is the last ask.
    best_bid = safe_float(book.bids[-1].price) if book.bids else None
    bid_size = safe_float(book.bids[-1].size) if book.bids else None
    best_ask = safe_float(book.asks[-1].price) if book.asks else None
    ask_size = safe_float(book.asks[-1].size) if book.asks else None
    return best_bid, best_ask, bid_size, ask_size


def compute_mid(best_bid: float | None, best_ask: float | None) -> float | None:
    if best_bid is not None and best_ask is not None:
        return (best_bid + best_ask) / 2.0
    return best_bid if best_bid is not None else best_ask


def compute_spread(best_bid: float | None, best_ask: float | None) -> float | None:
    if best_bid is None or best_ask is None:
        return None
    return max(0.0, best_ask - best_bid)


def snapshot_from_market_and_book(market, token, book) -> BookSnapshot:
    best_bid, best_ask, bid_size, ask_size = top_of_book(book)
    mid = compute_mid(best_bid, best_ask)
    spread = compute_spread(best_bid, best_ask)
    bid_depth = (
        best_bid * bid_size if best_bid is not None and bid_size is not None else None
    )
    ask_depth = (
        best_ask * ask_size if best_ask is not None and ask_size is not None else None
    )

    return BookSnapshot(
        token_id=token.token_id,
        market_id=market.id,
        question=market.question,
        outcome=token.outcome,
        gamma_price=token.price,
        best_bid=best_bid,
        best_ask=best_ask,
        bid_size=bid_size,
        ask_size=ask_size,
        bid_depth=bid_depth,
        ask_depth=ask_depth,
        mid_price=mid,
        spread=spread,
        liquidity=market.liquidity,
        volume=market.volume,
        ts=datetime.now(timezone.utc),
    )


def score_snapshot(
    snap: BookSnapshot,
    price_5m_ago: float | None,
    complement_ask_sum: float | None = None,
    complement_bid_sum: float | None = None,
) -> SignalResult:
    flags: list[str] = []

    price_change_5m = None
    if snap.mid_price is not None and price_5m_ago is not None:
        price_change_5m = snap.mid_price - price_5m_ago

    score = 0.0

    # Spread signal
    if snap.spread is not None:
        score += min(snap.spread / 0.1, 1.0) * 2.0
        if snap.spread >= 0.04:
            flags.append("wide_spread")

    # 5-minute price momentum
    if price_change_5m is not None:
        score += min(abs(price_change_5m) / 0.1, 1.0) * 1.5
        if abs(price_change_5m) >= 0.05:
            flags.append("fast_move")

    # Low liquidity
    if snap.liquidity is not None and snap.liquidity < 5000:
        score += 1.0
        flags.append("low_liquidity")

    # Extreme probability (near 0 or 1) — informational only
    if snap.mid_price is not None and (snap.mid_price < 0.05 or snap.mid_price > 0.95):
        flags.append("extreme_probability")

    # Gamma divergence: CLOB mid vs Gamma API reference price
    gamma_divergence = None
    if snap.mid_price is not None and snap.gamma_price is not None:
        gamma_divergence = abs(snap.mid_price - snap.gamma_price)
        score += min(gamma_divergence / 0.05, 1.0) * 1.0
        if gamma_divergence >= 0.03:
            flags.append("gamma_gap")

    # Complementary arbitrage check
    arb_gap = None
    if complement_ask_sum is not None:
        buy_gap = 1.0 - complement_ask_sum
        if buy_gap > 0.001:
            arb_gap = buy_gap
            score += min(buy_gap / 0.05, 1.0) * 2.0
            flags.append(f"buy_arb:{buy_gap:+.3f}")
    if complement_bid_sum is not None:
        sell_gap = complement_bid_sum - 1.0
        if sell_gap > 0.001:
            if arb_gap is None:
                arb_gap = -sell_gap
            score += min(sell_gap / 0.05, 1.0) * 2.0
            flags.append(f"sell_arb:{sell_gap:+.3f}")

    # Thin book warning
    min_depth = None
    if snap.bid_depth is not None and snap.ask_depth is not None:
        min_depth = min(snap.bid_depth, snap.ask_depth)
    elif snap.bid_depth is not None:
        min_depth = snap.bid_depth
    elif snap.ask_depth is not None:
        min_depth = snap.ask_depth
    if min_depth is not None and min_depth < 100:
        flags.append("thin_book")

    return SignalResult(
        token_id=snap.token_id,
        market_id=snap.market_id,
        question=snap.question,
        outcome=snap.outcome,
        mid_price=snap.mid_price,
        spread=snap.spread,
        price_change_5m=price_change_5m,
        gamma_divergence=gamma_divergence,
        arb_gap=arb_gap,
        bid_depth=snap.bid_depth,
        ask_depth=snap.ask_depth,
        liquidity=snap.liquidity,
        volume=snap.volume,
        score=score,
        flags=flags,
    )
