from datetime import datetime
from decimal import Decimal

import pytest
import pytest_asyncio

from app.domain.entities import (
    NotificationStatus,
    Observation,
    ObservationType,
)


def _obs(**kwargs):
    defaults = dict(
        source_id=1,
        observation_type=ObservationType.PRODUCT,
        observed_at=datetime.utcnow(),
    )
    defaults.update(kwargs)
    return Observation(**defaults)


class TestObservationCRUD:
    @pytest.mark.asyncio
    async def test_insert_observation(self, db):
        obs = _obs(
            source_id=1,
            external_id="test-ext-001",
            observation_type=ObservationType.PRODUCT,
            title="Kindle Paperwhite",
            price=Decimal("89.99"),
            currency="USD",
            url="https://example.com/kindle",
        )
        obs_id = await db.insert_observation(obs)
        assert obs_id > 0

    @pytest.mark.asyncio
    async def test_observation_exists_positive(self, db):
        obs = _obs(
            source_id=1,
            external_id="test-ext-002",
            observation_type=ObservationType.PRODUCT,
            title="Kindle",
        )
        await db.insert_observation(obs)
        exists = await db.observation_exists(1, "test-ext-002")
        assert exists is True

    @pytest.mark.asyncio
    async def test_observation_exists_negative(self, db):
        exists = await db.observation_exists(1, "nonexistent-id")
        assert exists is False

    @pytest.mark.asyncio
    async def test_observation_exists_different_source(self, db):
        obs = _obs(
            source_id=1,
            external_id="test-ext-003",
            observation_type=ObservationType.PRODUCT,
            title="Kindle",
        )
        await db.insert_observation(obs)
        exists = await db.observation_exists(2, "test-ext-003")
        assert exists is False

    @pytest.mark.asyncio
    async def test_insert_observation_with_all_fields(self, db):
        obs = _obs(
            source_id=1,
            external_id="test-ext-004",
            observation_type=ObservationType.COUPON,
            title="Kindle deal with coupon",
            price=Decimal("79.50"),
            currency="USD",
            coupon="KINDLE25",
            url="https://example.com/deal",
            raw_content="Full post content here",
        )
        obs_id = await db.insert_observation(obs)
        assert obs_id > 0
        exists = await db.observation_exists(1, "test-ext-004")
        assert exists is True


class TestNotificationCRUD:
    @pytest.mark.asyncio
    async def test_insert_notification(self, db):
        obs = _obs(
            source_id=1,
            external_id="test-ext-005",
            observation_type=ObservationType.PRODUCT,
            title="Kindle",
        )
        obs_id = await db.insert_observation(obs)
        notif_id = await db.insert_notification(obs_id, "telegram", "SUCCESS")
        assert notif_id > 0

    @pytest.mark.asyncio
    async def test_notification_exists(self, db):
        obs = _obs(
            source_id=1,
            external_id="test-ext-006",
            observation_type=ObservationType.PRODUCT,
            title="Kindle",
        )
        obs_id = await db.insert_observation(obs)
        await db.insert_notification(obs_id, "telegram", "SUCCESS")
        exists = await db.notification_exists(obs_id)
        assert exists is True

    @pytest.mark.asyncio
    async def test_notification_exists_negative(self, db):
        exists = await db.notification_exists(999999)
        assert exists is False

    @pytest.mark.asyncio
    async def test_update_notification_status(self, db):
        obs = _obs(
            source_id=1,
            external_id="test-ext-007",
            observation_type=ObservationType.PRODUCT,
            title="Kindle",
        )
        obs_id = await db.insert_observation(obs)
        notif_id = await db.insert_notification(obs_id, "telegram", "SUCCESS")
        await db.update_notification_status(notif_id, "FAILED")

        async with db._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT status FROM notifications WHERE id = $1", notif_id
            )
        assert row["status"] == "FAILED"

    @pytest.mark.asyncio
    async def test_update_notification_message_id(self, db):
        obs = _obs(
            source_id=1,
            external_id="test-ext-008",
            observation_type=ObservationType.PRODUCT,
            title="Kindle",
        )
        obs_id = await db.insert_observation(obs)
        notif_id = await db.insert_notification(obs_id, "telegram", "SUCCESS")
        await db.update_notification_message_id(notif_id, 12345)

        found = await db.find_notification_by_message_id(12345)
        assert found is not None
        assert found["id"] == notif_id

    @pytest.mark.asyncio
    async def test_find_notification_by_message_id_missing(self, db):
        found = await db.find_notification_by_message_id(99999)
        assert found is None

    @pytest.mark.asyncio
    async def test_insert_feedback(self, db):
        obs = _obs(
            source_id=1,
            external_id="test-ext-009",
            observation_type=ObservationType.PRODUCT,
            title="Kindle",
        )
        obs_id = await db.insert_observation(obs)
        notif_id = await db.insert_notification(obs_id, "telegram", "SUCCESS")
        await db.insert_feedback(notif_id, "\U0001f44d")

        async with db._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT reaction FROM notification_feedback "
                "WHERE notification_id = $1",
                notif_id,
            )
        assert row is not None
        assert row["reaction"] == "\U0001f44d"


class TestSourceAndWatchTerms:
    @pytest.mark.asyncio
    async def test_load_sources(self, db):
        sources = await db.load_sources()
        assert "woot" in sources
        assert "reddit" in sources
        assert "telegram" in sources
        assert sources["woot"].enabled is True

    @pytest.mark.asyncio
    async def test_load_watch_terms(self, db):
        terms = await db.load_watch_terms()
        assert len(terms) >= 1
        for watch_item_id, term_list in terms.items():
            assert len(term_list) > 0
            anchors = [t for t in term_list if t.term_type.value == "ANCHOR"]
            excludes = [t for t in term_list if t.term_type.value == "EXCLUDE"]
            assert len(anchors) > 0
            assert len(excludes) > 0


class TestSeedIdempotency:
    @pytest.mark.asyncio
    async def test_seed_defaults_idempotent(self, db):
        await db.seed_defaults()

        async with db._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT COUNT(*) AS cnt FROM sources"
            )
        count = row["cnt"]
        await db.seed_defaults()
        await db.seed_defaults()

        async with db._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT COUNT(*) AS cnt FROM sources"
            )
        assert row["cnt"] == count


class TestWatchItemUpdates:
    @pytest.mark.asyncio
    async def test_update_observation_watch_item(self, db):
        obs = _obs(
            source_id=1,
            external_id="test-ext-010",
            observation_type=ObservationType.PRODUCT,
            title="Kindle",
        )
        obs_id = await db.insert_observation(obs)
        sources = await db.load_sources()
        terms = await db.load_watch_terms()
        watch_item_id = list(terms.keys())[0]

        await db.update_observation_watch_item(obs_id, watch_item_id)

        async with db._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT watch_item_id FROM observations WHERE id = $1",
                obs_id,
            )
        assert row["watch_item_id"] == watch_item_id


class TestDailyStats:
    @pytest.mark.asyncio
    async def test_get_daily_stats_empty(self, db):
        stats = await db.get_daily_stats()
        assert stats["notified"] == 0
        assert stats["errors"] == 0

    @pytest.mark.asyncio
    async def test_get_daily_stats_with_data(self, db):
        obs = _obs(
            source_id=1,
            external_id="test-ext-011",
            observation_type=ObservationType.PRODUCT,
            title="Kindle Paperwhite",
        )
        obs_id = await db.insert_observation(obs)
        notif_id = await db.insert_notification(obs_id, "telegram", "SUCCESS")

        sources = await db.load_sources()
        terms = await db.load_watch_terms()
        watch_item_id = list(terms.keys())[0]
        await db.update_observation_watch_item(obs_id, watch_item_id)

        stats = await db.get_daily_stats()
        assert stats["notified"] >= 1
        source_stats = stats["sources"]
        assert "woot" in source_stats
        assert source_stats["woot"]["observations"] >= 1
        assert source_stats["woot"]["matches"] >= 1
