from __future__ import annotations

import asyncio

from rich.console import Console
from rich.table import Table

from app.client import PolymarketClient
from app.scanner import snapshot_from_market_and_book, score_snapshot
from app.storage import SnapshotStore

console = Console()


async def run_scanner(limit: int = 25) -> None:
    store = SnapshotStore()

    async with PolymarketClient() as client:
        markets = await client.list_markets(limit=limit)
        results = []

        for market in markets:
            if not market.tokens:
                continue

            for token in market.tokens:
                if not token.token_id:
                    continue

                try:
                    book = await client.get_orderbook(token.token_id)
                except Exception as exc:
                    console.print(
                        f"[red]book fetch failed[/red] token={token.token_id} err={exc}"
                    )
                    continue

                snap = snapshot_from_market_and_book(market, token, book)
                store.insert_snapshot(snap)

                price_5m_ago = store.get_mid_price_minutes_ago(token.token_id, 5)
                result = score_snapshot(snap, price_5m_ago)
                results.append(result)

        results.sort(key=lambda r: r.score, reverse=True)

        table = Table(title="Polymarket Mispricing Scanner")
        table.add_column("Score")
        table.add_column("Question", overflow="fold")
        table.add_column("Outcome")
        table.add_column("Mid")
        table.add_column("Spread")
        table.add_column("5m Δ")
        table.add_column("Liquidity")
        table.add_column("Flags")

        for r in results[:20]:
            table.add_row(
                f"{r.score:.2f}",
                r.question or "",
                r.outcome or "",
                f"{r.mid_price:.3f}" if r.mid_price is not None else "-",
                f"{r.spread:.3f}" if r.spread is not None else "-",
                f"{r.price_change_5m:+.3f}" if r.price_change_5m is not None else "-",
                f"{r.liquidity:.0f}" if r.liquidity is not None else "-",
                ", ".join(r.flags),
            )

        console.print(table)


if __name__ == "__main__":
    asyncio.run(run_scanner())
