from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.healthcheck import check_health

_utcnow = lambda: datetime.now(timezone.utc).replace(tzinfo=None)


class TestHealthcheck:
    @pytest.mark.asyncio
    @patch("app.healthcheck.asyncpg.connect")
    async def test_db_unreachable(self, mock_connect):
        mock_connect.side_effect = OSError("Connection refused")
        assert await check_health() is False

    @pytest.mark.asyncio
    @patch("app.healthcheck.asyncpg.connect")
    async def test_db_reachable_fresh_install(self, mock_connect):
        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = {"last_obs": None, "total": 0}
        mock_connect.return_value = mock_conn

        assert await check_health() is True

    @pytest.mark.asyncio
    @patch("app.healthcheck.asyncpg.connect")
    async def test_db_reachable_recent_obs(self, mock_connect):
        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = {
            "last_obs": _utcnow() - timedelta(minutes=5),
            "total": 100,
        }
        mock_connect.return_value = mock_conn

        assert await check_health() is True

    @pytest.mark.asyncio
    @patch("app.healthcheck.asyncpg.connect")
    async def test_db_reachable_stale_obs(self, mock_connect):
        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = {
            "last_obs": _utcnow() - timedelta(minutes=90),
            "total": 100,
        }
        mock_connect.return_value = mock_conn

        assert await check_health() is False

    @pytest.mark.asyncio
    @patch("app.healthcheck.asyncpg.connect")
    async def test_db_query_timeout(self, mock_connect):
        mock_conn = AsyncMock()
        mock_conn.fetchrow.side_effect = TimeoutError("Query timeout")
        mock_connect.return_value = mock_conn

        assert await check_health() is False

    @pytest.mark.asyncio
    @patch("app.healthcheck.asyncpg.connect")
    async def test_obs_exactly_at_cutoff(self, mock_connect):
        from app.healthcheck import OBSERVATION_STALE_MINUTES

        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = {
            "last_obs": _utcnow()
            - timedelta(minutes=OBSERVATION_STALE_MINUTES)
            + timedelta(seconds=1),
            "total": 50,
        }
        mock_connect.return_value = mock_conn

        assert await check_health() is True

    @pytest.mark.asyncio
    @patch("app.healthcheck.asyncpg.connect")
    async def test_conn_closes_after_success(self, mock_connect):
        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = {"last_obs": None, "total": 0}
        mock_connect.return_value = mock_conn

        await check_health()
        mock_conn.close.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("app.healthcheck.asyncpg.connect")
    async def test_conn_closes_after_query_error(self, mock_connect):
        mock_conn = AsyncMock()
        mock_conn.fetchrow.side_effect = RuntimeError("query error")
        mock_connect.return_value = mock_conn

        await check_health()
        mock_conn.close.assert_awaited_once()
