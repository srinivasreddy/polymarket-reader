from __future__ import annotations

import sqlite3

from app.models import BookSnapshot


class SnapshotStore:
    def __init__(self, db_path: str = "polymarket.db") -> None:
        self.conn = sqlite3.connect(db_path)
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS snapshots (
                token_id TEXT NOT NULL,
                market_id TEXT,
                question TEXT,
                outcome TEXT,
                best_bid REAL,
                best_ask REAL,
                mid_price REAL,
                spread REAL,
                liquidity REAL,
                volume REAL,
                ts TEXT NOT NULL
            )
            """
        )
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_snapshots_token_ts ON snapshots(token_id, ts)"
        )
        self.conn.commit()

    def insert_snapshot(self, snap: BookSnapshot) -> None:
        self.conn.execute(
            """
            INSERT INTO snapshots (
                token_id, market_id, question, outcome,
                best_bid, best_ask, mid_price, spread,
                liquidity, volume, ts
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                snap.token_id,
                snap.market_id,
                snap.question,
                snap.outcome,
                snap.best_bid,
                snap.best_ask,
                snap.mid_price,
                snap.spread,
                snap.liquidity,
                snap.volume,
                snap.ts.isoformat(),
            ),
        )
        self.conn.commit()

    def get_mid_price_minutes_ago(self, token_id: str, minutes: int) -> float | None:
        row = self.conn.execute(
            """
            SELECT mid_price
            FROM snapshots
            WHERE token_id = ?
              AND ts <= datetime('now', ?)
              AND mid_price IS NOT NULL
            ORDER BY ts DESC
            LIMIT 1
            """,
            (token_id, f"-{minutes} minutes"),
        ).fetchone()
        return float(row[0]) if row else None
