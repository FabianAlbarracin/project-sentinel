import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import pytest_asyncio

from app.collectors.reddit.collector import (
    RedditCollector,
    _extract_coupon_code,
)
from app.collectors.telegram.collector import (
    TelegramCollector,
    _parse_channels,
)
from app.collectors.woot.collector import WootCollector
from app.infrastructure.config import Settings


FIXTURES = Path(__file__).parent / "fixtures"


class _MockResponse:
    def __init__(self, status=200, body=None, json_data=None, headers=None):
        self.status = status
        self._body = body
        self._json = json_data
        self.headers = headers or {}

    async def text(self):
        return self._body or ""

    async def json(self):
        return self._json or {}

    def raise_for_status(self):
        if self.status >= 400:
            from aiohttp import ClientResponseError
            raise ClientResponseError(
                request_info=MagicMock(),
                history=(),
                status=self.status,
            )


class _MockCtx:
    def __init__(self, response):
        self._response = response

    async def __aenter__(self):
        return self._response

    async def __aexit__(self, *args):
        pass

    def __await__(self):
        async def _dummy():
            return self._response
        return _dummy().__await__()


def _mock_get(status=200, body=None, json_data=None, headers=None):
    resp = _MockResponse(
        status=status, body=body, json_data=json_data, headers=headers,
    )
    return _MockCtx(resp)


class TestWootCollector:
    @pytest.mark.asyncio
    async def test_collect_maps_items_to_observations(self):
        with open(FIXTURES / "woot_feed.json") as f:
            items = json.load(f)
        items = [i for i in items if not i.get("IsSoldOut")]
        if items:
            items[0]["OfferId"] = "kindle-offer-001"
            items[0]["Title"] = "Amazon Kindle Paperwhite"
            items[0]["SalePrice"] = {"Minimum": 89.99, "Maximum": 89.99}

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=_mock_get(
            json_data={"Items": items},
        ))

        collector = WootCollector(
            name="woot",
            interval_seconds=900,
            source_id=1,
            api_key="test-key",
        )
        collector._session = mock_session

        observations = await collector.collect()

        assert len(observations) > 0
        assert observations[0].source_id == 1
        assert observations[0].observation_type.value == "PRODUCT"
        assert observations[0].currency == "USD"

    @pytest.mark.asyncio
    async def test_filters_sold_out_items(self):
        items = [
            {
                "OfferId": "sold-001",
                "Title": "Sold Out Kindle",
                "IsSoldOut": True,
                "SalePrice": {"Minimum": 49.99, "Maximum": 49.99},
                "Url": "https://woot.com/sold",
                "StartDate": "2026-07-09T00:00:00+00:00",
            },
            {
                "OfferId": "avail-001",
                "Title": "Available Kindle",
                "IsSoldOut": False,
                "SalePrice": {"Minimum": 89.99, "Maximum": 89.99},
                "Url": "https://woot.com/avail",
                "StartDate": "2026-07-09T00:00:00+00:00",
            },
        ]

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=_mock_get(
            json_data={"Items": items},
        ))

        collector = WootCollector(
            name="woot",
            interval_seconds=900,
            source_id=1,
            api_key="test-key",
        )
        collector._session = mock_session

        observations = await collector.collect()

        assert len(observations) == 1
        assert observations[0].external_id == "avail-001"

    @pytest.mark.asyncio
    async def test_no_api_key_returns_empty(self):
        collector = WootCollector(
            name="woot",
            interval_seconds=900,
            source_id=1,
            api_key=None,
        )
        observations = await collector.collect()
        assert observations == []

    @pytest.mark.asyncio
    async def test_handles_403(self):
        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=_mock_get(status=403))

        collector = WootCollector(
            name="woot",
            interval_seconds=900,
            source_id=1,
            api_key="bad-key",
        )
        collector._session = mock_session

        observations = await collector.collect()
        assert observations == []

    @pytest.mark.asyncio
    async def test_retry_on_429(self):
        success_ctx = _mock_get(
            json_data={
                "Items": [
                    {
                        "OfferId": "retry-001",
                        "Title": "Kindle After Retry",
                        "IsSoldOut": False,
                        "SalePrice": {"Minimum": 79.99, "Maximum": 79.99},
                        "Url": "https://woot.com/retry",
                        "StartDate": "2026-07-09T00:00:00+00:00",
                    }
                ]
            },
        )
        rate_limit_ctx = _mock_get(status=429, headers={"Retry-After": "1"})

        mock_session = MagicMock()
        mock_session.get = MagicMock(side_effect=[rate_limit_ctx, success_ctx])

        collector = WootCollector(
            name="woot",
            interval_seconds=900,
            source_id=1,
            api_key="test-key",
        )
        collector._session = mock_session

        observations = await collector.collect()
        assert len(observations) == 1
        assert observations[0].external_id == "retry-001"


class TestRedditCollector:
    @pytest.mark.asyncio
    async def test_collect_maps_deal_posts(self):
        html = (FIXTURES / "reddit_listing.html").read_text()

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=_mock_get(body=html))

        collector = RedditCollector(
            name="reddit",
            interval_seconds=600,
            source_id=2,
        )
        collector._session = mock_session

        observations = await collector.collect()
        assert len(observations) > 0
        for obs in observations:
            if obs.external_id:
                assert isinstance(obs.external_id, str)
            assert obs.source_id == 2

    @pytest.mark.asyncio
    async def test_classify_coupon_post(self):
        from app.collectors.reddit.collector import _classify_post
        from app.domain.entities import ObservationType

        obs_type = _classify_post("Kindle coupon code KINDLE25 here", "")
        assert obs_type == ObservationType.COUPON

        obs_type = _classify_post("Kindle on sale at Target", "")
        assert obs_type == ObservationType.POST

    @pytest.mark.asyncio
    async def test_extract_coupon_from_real_post(self):
        code = _extract_coupon_code(
            "Use code KINDLE25 for 20% off Kindle", ""
        )
        assert code == "KINDLE25"

    @pytest.mark.asyncio
    async def test_handles_404_subreddit(self):
        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=_mock_get(status=404))

        collector = RedditCollector(
            name="reddit",
            interval_seconds=600,
            source_id=2,
            subreddits=["nonexistent_sub"],
        )
        collector._session = mock_session

        observations = await collector.collect()
        assert observations == []


class TestTelegramCollector:
    @pytest.mark.asyncio
    async def test_collect_maps_deal_messages(self):
        html = (FIXTURES / "telegram_channel.html").read_text()

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=_mock_get(body=html))

        collector = TelegramCollector(
            name="telegram",
            interval_seconds=300,
            source_id=3,
            channels=["Clubgratis"],
        )
        collector._session = mock_session

        observations = await collector.collect()
        assert len(observations) > 0
        for obs in observations:
            assert obs.source_id == 3
            assert obs.external_id is not None

    @pytest.mark.asyncio
    async def test_no_channels_returns_empty(self):
        collector = TelegramCollector(
            name="telegram",
            interval_seconds=300,
            source_id=3,
            channels=[],
        )
        observations = await collector.collect()
        assert observations == []

    @pytest.mark.asyncio
    async def test_handles_404_channel(self):
        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=_mock_get(status=404))

        collector = TelegramCollector(
            name="telegram",
            interval_seconds=300,
            source_id=3,
            channels=["nonexistent"],
        )
        collector._session = mock_session

        observations = await collector.collect()
        assert observations == []
