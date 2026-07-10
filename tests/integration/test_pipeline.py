from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from app.domain.entities import (
    Observation,
    ObservationType,
    TermType,
    WatchTerm,
)
from app.domain.services import Processor
from app.infrastructure.notifications import TelegramNotifier


@pytest.fixture
def processor():
    terms = {
        1: [
            WatchTerm(1, 1, "kindle", TermType.ANCHOR, None),
            WatchTerm(2, 1, "paperwhite", TermType.ANCHOR, None),
            WatchTerm(3, 1, "case", TermType.EXCLUDE, None),
            WatchTerm(4, 1, "ebook", TermType.EXCLUDE, None),
        ]
    }
    return Processor(terms)


async def _run_pipeline(db, observations, processor, notifier, sources_by_id,
                        max_per_cycle=500):
    stored = 0
    duplicates = 0
    failures = 0
    matches = 0
    notified = 0

    if len(observations) > max_per_cycle:
        observations = observations[:max_per_cycle]

    for obs in observations:
        try:
            if obs.external_id:
                exists = await db.observation_exists(obs.source_id, obs.external_id)
                if exists:
                    duplicates += 1
                    continue

            obs_id = await db.insert_observation(obs)
            stored += 1

            watch_item_id = processor.match_observation(obs)
            if watch_item_id is None:
                continue

            matches += 1
            await db.update_observation_watch_item(obs_id, watch_item_id)

            already_notified = await db.notification_exists(obs_id)
            if already_notified:
                continue

            notif_id = await db.insert_notification(obs_id, "telegram", "SUCCESS")

            if notifier is not None:
                source = sources_by_id.get(obs.source_id)
                source_name = source.name if source else "unknown"
                message_id = await notifier.send(obs, source_name)
                if message_id is not None:
                    await db.update_notification_message_id(notif_id, message_id)
                    notified += 1
                else:
                    await db.update_notification_status(notif_id, "FAILED")
        except Exception:
            failures += 1

    return {
        "stored": stored,
        "duplicates": duplicates,
        "failures": failures,
        "matches": matches,
        "notified": notified,
    }


def _make_obs(source_id=1, external_id=None, obs_type=ObservationType.PRODUCT,
              title=None, url=None, price=None):
    return Observation(
        source_id=source_id,
        external_id=external_id,
        observed_at=datetime.utcnow(),
        observation_type=obs_type,
        title=title,
        price=price,
        currency="USD",
        url=url,
    )


class TestPipelineFullFlow:
    @pytest.mark.asyncio
    async def test_full_flow_match_and_notify(self, db, processor):
        mock_notifier = AsyncMock(spec=TelegramNotifier)
        mock_notifier.send.return_value = 10042
        sources_by_id = {1: type("S", (), {"id": 1, "name": "woot"})()}

        obs = _make_obs(
            source_id=1,
            external_id="pipeline-001",
            title="Kindle Paperwhite on sale",
            price=Decimal("89.99"),
            url="https://example.com",
        )

        result = await _run_pipeline(
            db, [obs], processor, mock_notifier, sources_by_id,
        )

        assert result["stored"] == 1
        assert result["matches"] == 1
        assert result["notified"] == 1
        assert result["duplicates"] == 0

    @pytest.mark.asyncio
    async def test_duplicate_skipped(self, db, processor):
        mock_notifier = AsyncMock(spec=TelegramNotifier)
        mock_notifier.send.return_value = 10042
        sources_by_id = {1: type("S", (), {"id": 1, "name": "woot"})()}

        obs = _make_obs(
            source_id=1,
            external_id="pipeline-002",
            title="Kindle Paperwhite",
        )

        result1 = await _run_pipeline(
            db, [obs], processor, mock_notifier, sources_by_id,
        )
        result2 = await _run_pipeline(
            db, [obs], processor, mock_notifier, sources_by_id,
        )

        assert result1["duplicates"] == 0
        assert result2["duplicates"] == 1
        assert result2["stored"] == 0

    @pytest.mark.asyncio
    async def test_no_match_no_notification(self, db, processor):
        mock_notifier = AsyncMock(spec=TelegramNotifier)
        mock_notifier.send.return_value = 10042
        sources_by_id = {1: type("S", (), {"id": 1, "name": "woot"})()}

        obs = _make_obs(
            source_id=1,
            external_id="pipeline-003",
            title="iPhone case for sale",
        )

        result = await _run_pipeline(
            db, [obs], processor, mock_notifier, sources_by_id,
        )

        assert result["stored"] == 1
        assert result["matches"] == 0
        assert result["notified"] == 0
        mock_notifier.send.assert_not_called()

    @pytest.mark.asyncio
    async def test_already_notified_skipped(self, db, processor):
        mock_notifier = AsyncMock(spec=TelegramNotifier)
        mock_notifier.send.return_value = 10042
        sources_by_id = {1: type("S", (), {"id": 1, "name": "woot"})()}

        obs = _make_obs(
            source_id=1,
            external_id="pipeline-004",
            title="Kindle Scribe deal",
        )

        result1 = await _run_pipeline(
            db, [obs], processor, mock_notifier, sources_by_id,
        )
        assert result1["notified"] == 1

        obs2 = _make_obs(
            source_id=1,
            external_id="pipeline-004b",
            title="Kindle Scribe another post",
        )
        result2 = await _run_pipeline(
            db, [obs2], processor, mock_notifier, sources_by_id,
        )
        assert result2["notified"] == 1

        assert mock_notifier.send.call_count == 2

    @pytest.mark.asyncio
    async def test_batch_mixed(self, db, processor):
        mock_notifier = AsyncMock(spec=TelegramNotifier)
        mock_notifier.send.return_value = 10042
        sources_by_id = {1: type("S", (), {"id": 1, "name": "woot"})()}

        obs_list = [
            _make_obs(source_id=1, external_id="batch-001", title="Kindle on sale"),
            _make_obs(source_id=1, external_id="batch-002", title="Coffee maker"),
            _make_obs(source_id=1, external_id="batch-001", title="Kindle on sale"),
            _make_obs(source_id=1, external_id="batch-003", title="Paperwhite deal"),
        ]

        result = await _run_pipeline(
            db, obs_list, processor, mock_notifier, sources_by_id,
        )

        assert result["stored"] == 3
        assert result["duplicates"] == 1
        assert result["matches"] == 2
        assert result["notified"] == 2

    @pytest.mark.asyncio
    async def test_failure_isolation(self, db, processor):
        mock_notifier = AsyncMock(spec=TelegramNotifier)
        mock_notifier.send.return_value = 10042
        sources_by_id = {1: type("S", (), {"id": 1, "name": "woot"})()}

        obs_list = [
            _make_obs(source_id=1, external_id="iso-001", title="Kindle deal"),
            _make_obs(source_id=1, external_id=None, title=None),
            _make_obs(source_id=1, external_id="iso-002", title="Paperwhite sale"),
        ]

        result = await _run_pipeline(
            db, obs_list, processor, mock_notifier, sources_by_id,
        )

        assert result["stored"] >= 2
        assert result["matches"] >= 2
        assert result["notified"] >= 2

    @pytest.mark.asyncio
    async def test_notifier_none(self, db, processor):
        sources_by_id = {1: type("S", (), {"id": 1, "name": "woot"})()}

        obs = _make_obs(
            source_id=1,
            external_id="pipeline-005",
            title="Kindle Paperwhite discount",
        )

        result = await _run_pipeline(
            db, [obs], processor, None, sources_by_id,
        )

        assert result["stored"] == 1
        assert result["matches"] == 1
        assert result["notified"] == 0

    @pytest.mark.asyncio
    async def test_match_persists_watch_item_id(self, db, processor):
        mock_notifier = AsyncMock(spec=TelegramNotifier)
        mock_notifier.send.return_value = 10042
        sources_by_id = {1: type("S", (), {"id": 1, "name": "woot"})()}

        obs = _make_obs(
            source_id=1,
            external_id="pipeline-006",
            title="Kindle Scribe colorsoft",
        )

        await _run_pipeline(
            db, [obs], processor, mock_notifier, sources_by_id,
        )

        async with db._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT watch_item_id FROM observations "
                "WHERE external_id = $1",
                "pipeline-006",
            )
        assert row is not None
        assert row["watch_item_id"] is not None

    @pytest.mark.asyncio
    async def test_truncation_max_per_cycle(self, db, processor):
        mock_notifier = AsyncMock(spec=TelegramNotifier)
        mock_notifier.send.return_value = 10042
        sources_by_id = {1: type("S", (), {"id": 1, "name": "woot"})()}

        obs_list = []
        for i in range(10):
            obs_list.append(
                _make_obs(
                    source_id=1,
                    external_id=f"trunc-{i:03d}",
                    title=f"Kindle deal {i}",
                )
            )

        result = await _run_pipeline(
            db, obs_list, processor, mock_notifier, sources_by_id,
            max_per_cycle=3,
        )

        assert result["stored"] == 3
