from __future__ import annotations

import asyncio

from rich import print

from app.client import PolymarketClient


async def main() -> None:
    async with PolymarketClient() as client:
        markets = await client.list_markets(limit=5)

        print("\n[bold cyan]Latest active markets[/bold cyan]\n")
        for idx, market in enumerate(markets, start=1):
            print(f"{idx}. {market.question}")
            print(f"   id={market.id} liquidity={market.liquidity} volume={market.volume}")

            if market.tokens:
                for token in market.tokens:
                    print(
                        f"   - outcome={token.outcome!r} "
                        f"token_id={token.token_id} price={token.price}"
                    )

        first_token_id = None
        for market in markets:
            if market.tokens:
                for token in market.tokens:
                    if token.token_id:
                        first_token_id = token.token_id
                        break
            if first_token_id:
                break

        if first_token_id:
            book = await client.get_orderbook(first_token_id)
            print("\n[bold green]Order book[/bold green]\n")
            print(f"asset_id={book.asset_id}")
            print(f"top bids={book.bids[:3]}")
            print(f"top asks={book.asks[:3]}")


if __name__ == "__main__":
    asyncio.run(main())