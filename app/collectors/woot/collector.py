import asyncio
import logging
import random
from datetime import datetime
from decimal import Decimal
from typing import Optional

import aiohttp

from app.collectors.base import BaseCollector
from app.domain.entities import Observation, ObservationType

logger = logging.getLogger(__name__)

WOOT_API_BASE = "https://developer.woot.com"


class WootCollector(BaseCollector):
    def __init__(
        self,
        name: str,
        interval_seconds: int,
        source_id: int,
        api_key: Optional[str] = None,
    ):
        super().__init__(name, interval_seconds)
        self._source_id = source_id
        self._api_key = api_key
        self._session: Optional[aiohttp.ClientSession] = None

    async def start(self) -> None:
        self._session = aiohttp.ClientSession(
            headers={
                "Accept": "application/json",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "User-Agent": "ProjectSentinel/1.0 (Woot API client)",
                "x-api-key": self._api_key or "",
            },
        )
        await super().start()

    async def stop(self) -> None:
        if self._session:
            await self._session.close()
            self._session = None
        await super().stop()

    async def collect(self) -> list[Observation]:
        if not self._api_key:
            logger.warning(
                "Woot API key not configured; skipping collect cycle"
            )
            return []

        if not self._session:
            return []

        try:
            items = await self._fetch_feed()
        except Exception:
            logger.exception("Failed to fetch Woot feed")
            return []

        observations = []
        for item in items:
            if item.get("IsSoldOut"):
                continue

            offer_id = item.get("OfferId")
            if not offer_id:
                continue

            title = item.get("Title")
            url = item.get("Url")
            sale_price = item.get("SalePrice", {})
            price = sale_price.get("Minimum") if sale_price else None
            start_date = item.get("StartDate")

            observed_at = None
            if start_date:
                try:
                    observed_at = (
                        datetime.fromisoformat(start_date)
                        .replace(tzinfo=None)
                    )
                except (ValueError, TypeError):
                    pass

            observations.append(
                Observation(
                    source_id=self._source_id,
                    external_id=offer_id,
                    observed_at=observed_at or datetime.utcnow(),
                    observation_type=ObservationType.PRODUCT,
                    title=title,
                    price=Decimal(str(price)) if price is not None else None,
                    currency="USD",
                    url=url,
                )
            )

        logger.info(
            "Woot collect: %d items fetched, %d observations created",
            len(items),
            len(observations),
        )
        return observations

    async def _fetch_feed(self) -> list[dict]:
        url = f"{WOOT_API_BASE}/feed/All"
        max_retries = 3
        base_delay = 5

        for attempt in range(max_retries + 1):
            try:
                async with self._session.get(url) as resp:
                    if resp.status == 403:
                        logger.error("Woot API returned 403 (invalid API key?)")
                        return []
                    if resp.status == 429:
                        retry_after = resp.headers.get("Retry-After")
                        delay = float(retry_after) if retry_after else base_delay * (2 ** attempt) + random.uniform(0, 2)
                        logger.warning(
                            "Woot API rate limited (attempt %d/%d, retry in %.1fs)",
                            attempt + 1, max_retries + 1, delay,
                        )
                        if attempt < max_retries:
                            await asyncio.sleep(delay)
                            continue
                        return []
                    resp.raise_for_status()
                    data = await resp.json()
                    break
            except (aiohttp.ClientError, asyncio.TimeoutError):
                if attempt < max_retries:
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                    logger.warning(
                        "Woot API fetch error (attempt %d/%d, retry in %.1fs)",
                        attempt + 1, max_retries + 1, delay,
                    )
                    await asyncio.sleep(delay)
                    continue
                raise

        return data.get("Items", [])
