import logging
from typing import Optional

import asyncpg

from app.domain.entities import (
    Notification,
    NotificationStatus,
    Observation,
    ObservationType,
    Source,
    WatchItem,
    WatchTerm,
    TermType,
)

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, dsn: str):
        self._dsn = dsn
        self._pool: Optional[asyncpg.Pool] = None

    async def connect(self) -> None:
        self._pool = await asyncpg.create_pool(self._dsn, min_size=1, max_size=5)
        logger.info("Database pool created")

    async def disconnect(self) -> None:
        if self._pool:
            await self._pool.close()
            logger.info("Database pool closed")

    async def init_schema(self) -> None:
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS sources (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(255) NOT NULL UNIQUE,
                        enabled BOOLEAN NOT NULL DEFAULT TRUE,
                        created_at TIMESTAMP NOT NULL DEFAULT NOW()
                    );
                """)
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS watch_items (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(255) NOT NULL UNIQUE,
                        enabled BOOLEAN NOT NULL DEFAULT TRUE,
                        created_at TIMESTAMP NOT NULL DEFAULT NOW()
                    );
                """)
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS watch_terms (
                        id SERIAL PRIMARY KEY,
                        watch_item_id INTEGER NOT NULL REFERENCES watch_items(id),
                        term VARCHAR(255) NOT NULL,
                        term_type VARCHAR(50) NOT NULL DEFAULT 'ANCHOR',
                        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                        UNIQUE (watch_item_id, term)
                    );
                """)
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS observations (
                        id SERIAL PRIMARY KEY,
                        source_id INTEGER NOT NULL REFERENCES sources(id),
                        watch_item_id INTEGER REFERENCES watch_items(id),
                        external_id VARCHAR(512),
                        observed_at TIMESTAMP NOT NULL DEFAULT NOW(),
                        observation_type VARCHAR(50) NOT NULL DEFAULT 'UNKNOWN',
                        title TEXT,
                        price DECIMAL,
                        currency VARCHAR(10),
                        coupon VARCHAR(255),
                        url TEXT,
                        raw_content TEXT,
                        created_at TIMESTAMP NOT NULL DEFAULT NOW()
                    );
                """)
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_observations_external_id
                        ON observations (source_id, external_id);
                """)
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_observations_watch_item
                        ON observations (watch_item_id);
                """)
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS notifications (
                        id SERIAL PRIMARY KEY,
                        observation_id INTEGER NOT NULL REFERENCES observations(id),
                        channel VARCHAR(50) NOT NULL DEFAULT 'telegram',
                        status VARCHAR(50) NOT NULL DEFAULT 'SUCCESS',
                        telegram_message_id BIGINT,
                        sent_at TIMESTAMP NOT NULL DEFAULT NOW()
                    );
                """)
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS notification_feedback (
                        id SERIAL PRIMARY KEY,
                        notification_id INTEGER NOT NULL REFERENCES notifications(id),
                        reaction VARCHAR(50) NOT NULL,
                        created_at TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'UTC')
                    );
                """)
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_feedback_notification
                        ON notification_feedback (notification_id);
                """)
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS settings (
                        key VARCHAR(255) PRIMARY KEY,
                        value TEXT
                    );
                """)
        logger.info("Schema initialized")

    async def _migrate_schema(self) -> None:
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute("""
                    ALTER TABLE notifications
                    ADD COLUMN IF NOT EXISTS telegram_message_id BIGINT;
                """)
        logger.info("Schema migrations applied")

    async def seed_defaults(self) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO sources (name, enabled)
                VALUES ('woot', TRUE)
                ON CONFLICT (name) DO NOTHING;
            """)
            await conn.execute("""
                INSERT INTO sources (name, enabled)
                VALUES ('reddit', TRUE)
                ON CONFLICT (name) DO NOTHING;
            """)
            await conn.execute("""
                INSERT INTO sources (name, enabled)
                VALUES ('telegram', TRUE)
                ON CONFLICT (name) DO NOTHING;
            """)
            result = await conn.fetchrow(
                "INSERT INTO watch_items (name, enabled) "
                "VALUES ('Kindle', TRUE) "
                "ON CONFLICT (name) DO NOTHING "
                "RETURNING id;"
            )
            if result is None:
                result = await conn.fetchrow(
                    "SELECT id FROM watch_items WHERE name = 'Kindle';"
                )
            kindle_id = result["id"]

            anchor_terms = ["kindle", "paperwhite", "scribe"]
            exclude_terms = ["case", "cover", "protector", "skin", "sleeve",
                             "charger", "cable", "adapter", "screen protector",
                             "stand", "holder", "mount", "strap",
                             "ebook", "free book", "kindle edition",
                             "kindle ebook", "pdf", "software", "app",
                             "digest", "free ebook"]

            for term in anchor_terms:
                await conn.execute("""
                    INSERT INTO watch_terms (watch_item_id, term, term_type)
                    VALUES ($1, $2, 'ANCHOR')
                    ON CONFLICT (watch_item_id, term) DO NOTHING;
                """, kindle_id, term)

            for term in exclude_terms:
                await conn.execute("""
                    INSERT INTO watch_terms (watch_item_id, term, term_type)
                    VALUES ($1, $2, 'EXCLUDE')
                    ON CONFLICT (watch_item_id, term) DO NOTHING;
                """, kindle_id, term)

        logger.info("Default data seeded")

    async def load_sources(self) -> dict[str, Source]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT id, name, enabled, created_at FROM sources;
            """)
            return {
                row["name"]: Source(
                    id=row["id"],
                    name=row["name"],
                    enabled=row["enabled"],
                    created_at=row["created_at"],
                )
                for row in rows
            }

    async def load_watch_terms(self) -> dict[int, list[WatchTerm]]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT id, watch_item_id, term, term_type, created_at
                FROM watch_terms
                ORDER BY watch_item_id;
            """)
            result: dict[int, list[WatchTerm]] = {}
            for row in rows:
                wt = WatchTerm(
                    id=row["id"],
                    watch_item_id=row["watch_item_id"],
                    term=row["term"],
                    term_type=TermType(row["term_type"]),
                    created_at=row["created_at"],
                )
                result.setdefault(row["watch_item_id"], []).append(wt)
            return result

    async def observation_exists(
        self, source_id: int, external_id: str
    ) -> bool:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT 1 FROM observations "
                "WHERE source_id = $1 AND external_id = $2 LIMIT 1;",
                source_id, external_id,
            )
            return row is not None

    async def insert_observation(self, obs: Observation) -> int:
        from datetime import datetime
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO observations (
                    source_id, watch_item_id, external_id, observed_at,
                    observation_type, title, price, currency, coupon,
                    url, raw_content
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                RETURNING id;
                """,
                obs.source_id,
                obs.watch_item_id,
                obs.external_id,
                obs.observed_at or datetime.utcnow(),
                obs.observation_type.value,
                obs.title,
                obs.price,
                obs.currency,
                obs.coupon,
                obs.url,
                obs.raw_content,
            )
            return row["id"]

    async def notification_exists(self, observation_id: int) -> bool:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT 1 FROM notifications "
                "WHERE observation_id = $1 LIMIT 1;",
                observation_id,
            )
            return row is not None

    async def insert_notification(
        self, observation_id: int, channel: str, status: str
    ) -> int:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO notifications (observation_id, channel, status)
                VALUES ($1, $2, $3)
                RETURNING id;
                """,
                observation_id, channel, status,
            )
            return row["id"]

    async def update_notification_status(
        self, notification_id: int, status: str
    ) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                "UPDATE notifications SET status = $1 WHERE id = $2;",
                status, notification_id,
            )

    async def update_observation_watch_item(
        self, observation_id: int, watch_item_id: int
    ) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                "UPDATE observations SET watch_item_id = $1 WHERE id = $2;",
                watch_item_id, observation_id,
            )

    async def update_notification_message_id(
        self, notification_id: int, telegram_message_id: int
    ) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                "UPDATE notifications SET telegram_message_id = $1 WHERE id = $2;",
                telegram_message_id, notification_id,
            )

    async def find_notification_by_message_id(
        self, telegram_message_id: int
    ) -> Optional[dict]:
        async with self._pool.acquire() as conn:
            return await conn.fetchrow(
                "SELECT id, observation_id FROM notifications "
                "WHERE telegram_message_id = $1 LIMIT 1;",
                telegram_message_id,
            )

    async def insert_feedback(
        self, notification_id: int, reaction: str
    ) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO notification_feedback (notification_id, reaction) "
                "VALUES ($1, $2);",
                notification_id, reaction,
            )

    async def get_setting(self, key: str) -> Optional[str]:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT value FROM settings WHERE key = $1;", key
            )
            return row["value"] if row else None

    async def get_daily_stats(self) -> dict:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT
                    s.name AS source_name,
                    COUNT(o.id) AS observations,
                    COUNT(o.id) FILTER (WHERE o.watch_item_id IS NOT NULL) AS matches
                FROM observations o
                JOIN sources s ON s.id = o.source_id
                WHERE o.created_at >= CURRENT_DATE
                GROUP BY s.name
                ORDER BY s.name;
            """)

            notif_row = await conn.fetchrow("""
                SELECT
                    COUNT(*) AS sent,
                    COUNT(*) FILTER (WHERE n.status = 'FAILED') AS errors
                FROM notifications n
                WHERE n.sent_at >= CURRENT_DATE;
            """)

            latest_rows = await conn.fetch("""
                SELECT s.name, MAX(o.created_at) AS last_obs
                FROM observations o
                JOIN sources s ON s.id = o.source_id
                GROUP BY s.name;
            """)

        sources = {}
        for row in rows:
            sources[row["source_name"]] = {
                "observations": row["observations"],
                "matches": row["matches"],
            }

        latest = {}
        for row in latest_rows:
            latest[row["name"]] = row["last_obs"]

        return {
            "sources": sources,
            "notified": notif_row["sent"] if notif_row else 0,
            "errors": notif_row["errors"] if notif_row else 0,
            "latest": latest,
        }
