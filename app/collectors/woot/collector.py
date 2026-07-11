import asyncio
import logging
import random
import re
from datetime import datetime
from decimal import Decimal
from typing import Optional

import aiohttp

from app.collectors.base import BaseCollector
from app.domain.entities import Observation, ObservationType

logger = logging.getLogger(__name__)

WOOT_API_BASE = "https://developer.woot.com"
WOOT_ENDPOINTS = ["Computers"]

_COUPON_PATTERN = re.compile(
    r"(?i:\b(?:code|coupon|promo)\b)\s*:?\s*([A-Z0-9]{4,})"
)


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
        self._last_seen: Optional[str] = None

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

        all_items = []
        for endpoint in WOOT_ENDPOINTS:
            try:
                items = await self._fetch_endpoint(endpoint)
                all_items.extend(items)
            except Exception:
                logger.exception("Failed to fetch Woot/%s", endpoint)

        if not all_items:
            logger.warning("Woot collect: 0 items fetched across all endpoints")
            return []

        new_items = []
        new_last_seen = self._last_seen
        for item in all_items:
            start_date = item.get("StartDate")
            if start_date and self._last_seen and start_date <= self._last_seen:
                continue
            new_items.append(item)
            if start_date and (new_last_seen is None or start_date > new_last_seen):
                new_last_seen = start_date

        if new_last_seen:
            self._last_seen = new_last_seen

        observations = []
        for item in new_items:
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

            coupon_code = None
            if title:
                coupon_match = _COUPON_PATTERN.search(title)
                if coupon_match:
                    coupon_code = coupon_match.group(1).upper()

            observed_at = None
            if start_date:
                try:
                    observed_at = (
                        datetime.fromisoformat(start_date)
                        .replace(tzinfo=None)
                    )
                except (ValueError, TypeError):
                    pass

            obs_type = ObservationType.COUPON if coupon_code else ObservationType.PRODUCT

            observations.append(
                Observation(
                    source_id=self._source_id,
                    external_id=offer_id,
                    observed_at=observed_at or datetime.utcnow(),
                    observation_type=obs_type,
                    title=title,
                    price=Decimal(str(price)) if price is not None else None,
                    currency="USD",
                    coupon=coupon_code,
                    url=url,
                )
            )

        total_all = len(all_items)
        logger.info(
            "Woot collect: %d items across %d endpoints, %d new (%d observations after filters)",
            total_all,
            len(WOOT_ENDPOINTS),
            len(new_items),
            len(observations),
        )
        return observations

    async def _fetch_endpoint(self, endpoint: str) -> list[dict]:
        url = f"{WOOT_API_BASE}/feed/{endpoint}"
        max_retries = 3
        base_delay = 5

        for attempt in range(max_retries + 1):
            try:
                async with self._session.get(url) as resp:
                    if resp.status == 403:
                        logger.error(
                            "Woot/%s returned 403 (invalid API key?)", endpoint
                        )
                        return []
                    if resp.status == 429:
                        retry_after = resp.headers.get("Retry-After")
                        delay = (
                            float(retry_after)
                            if retry_after
                            else base_delay * (2 ** attempt) + random.uniform(0, 2)
                        )
                        logger.warning(
                            "Woot/%s rate limited (attempt %d/%d, retry in %.1fs)",
                            endpoint, attempt + 1, max_retries + 1, delay,
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
                        "Woot/%s fetch error (attempt %d/%d, retry in %.1fs)",
                        endpoint, attempt + 1, max_retries + 1, delay,
                    )
                    await asyncio.sleep(delay)
                    continue
                raise

        return data.get("Items", [])
