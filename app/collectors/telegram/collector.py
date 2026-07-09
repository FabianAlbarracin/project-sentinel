import asyncio
import logging
import random
import re
from datetime import datetime
from typing import Optional

import aiohttp
from bs4 import BeautifulSoup

from app.collectors.base import BaseCollector
from app.domain.entities import Observation, ObservationType

logger = logging.getLogger(__name__)

TELEGRAM_WEB_BASE = "https://t.me"
TELEGRAM_S_BASE = "https://t.me/s"
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

DEFAULT_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "User-Agent": "ProjectSentinel/1.0 (Telegram channel monitor)",
}

DEAL_SIGNALS = [
    "joylink.io", "mavely.app", "amazon", "woot",
    "#ad", "$", "usd", "comprar", "gratis",
    "kindle unlimited", "desde", "oferta",
    "promo", "descuento", "cupón", "coupon",
    "price", "deal", "temu",
]

EXCLUDE_PREFIXES = [
    "reporto", "reportó", "llegó", "llegada",
    "k .", "k.", "reporto llegada",
]

COUPON_KEYWORDS = [
    "coupon", "coupon code", "discount code", "discount",
    "promo code", "promo", "deal", "% off", "$ off",
    "save", "off code", "code:", "cupón", "codigo",
    "código", "descuento",
]

COUPON_CODE_RE = re.compile(r"\b([A-Z0-9]{5,20})\b")

COUPON_SKIP_WORDS = {
    "TODAY", "TOMORROW", "LIMITED", "SUBSCRIBE", "PLEASE",
    "COMMENT", "REMEMBER", "AMAZON", "KINDLE", "PAPERWHITE",
    "THREAD", "HELLO", "CHECK", "HEADS", "SERIES", "MODEL",
    "EDITION", "DOESNT", "DOES", "USING", "WOULD", "THERE",
    "ABOUT", "BEFORE", "DURING", "AFTER", "REVIEW", "DONT",
    "CHANNEL", "JOIN", "GROUP", "GRATIS", "COMPRAR",
}


def _parse_channels(raw: str) -> list[str]:
    if not raw:
        return []
    return [c.strip().lstrip("@") for c in raw.split(",") if c.strip()]


def _is_deal_message(text: str) -> bool:
    lower = text.lower().strip()

    for prefix in EXCLUDE_PREFIXES:
        if lower.startswith(prefix):
            return False

    for signal in DEAL_SIGNALS:
        if signal in lower:
            return True

    return False


def _classify_message(text: str) -> ObservationType:
    lower = text.lower()
    for kw in COUPON_KEYWORDS:
        if kw in lower:
            return ObservationType.COUPON
    return ObservationType.POST


def _extract_coupon_code(text: str) -> Optional[str]:
    matches = COUPON_CODE_RE.findall(text)
    for m in matches:
        if m not in COUPON_SKIP_WORDS and not re.fullmatch(r"\d+", m):
            return m
    return None


class TelegramCollector(BaseCollector):
    def __init__(
        self,
        name: str,
        interval_seconds: int,
        source_id: int,
        channels: Optional[list[str]] = None,
    ):
        super().__init__(name, interval_seconds)
        self._source_id = source_id
        self._channels = channels or []
        self._session: Optional[aiohttp.ClientSession] = None

    async def start(self) -> None:
        self._session = aiohttp.ClientSession(headers=DEFAULT_HEADERS)
        if self._channels:
            logger.info(
                "Telegram collector monitoring %d channel(s): %s",
                len(self._channels),
                ", ".join(self._channels),
            )
        else:
            logger.warning(
                "Telegram collector has no channels configured; "
                "no messages will be collected"
            )
        await super().start()

    async def stop(self) -> None:
        if self._session:
            await self._session.close()
            self._session = None
        await super().stop()

    async def collect(self) -> list[Observation]:
        if not self._session or not self._channels:
            return []

        observations: list[Observation] = []
        total_fetched = 0

        for channel in self._channels:
            try:
                messages = await self._fetch_channel(channel)
                total_fetched += len(messages)
                for msg in messages:
                    text = msg.get("text", "")
                    if not _is_deal_message(text):
                        continue
                    obs = self._map_to_observation(msg, channel)
                    if obs:
                        observations.append(obs)
            except Exception:
                logger.exception("Failed to fetch @%s", channel)

            if len(self._channels) > 1:
                await asyncio.sleep(random.uniform(1, 3))

        logger.info(
            "Telegram collect: %d observations (deal-filtered from %d messages) "
            "across %d channel(s)",
            len(observations),
            total_fetched,
            len(self._channels),
        )
        return observations

    async def _fetch_channel(self, channel: str) -> list[dict]:
        url = f"{TELEGRAM_S_BASE}/{channel}"
        max_retries = 3
        base_delay = 5

        for attempt in range(max_retries + 1):
            try:
                async with self._session.get(url) as resp:
                    if resp.status == 404:
                        logger.warning("Channel @%s not found", channel)
                        return []
                    if resp.status == 429:
                        retry_after = resp.headers.get("Retry-After")
                        delay = float(retry_after) if retry_after else base_delay * (2 ** attempt) + random.uniform(0, 2)
                        logger.warning(
                            "Telegram rate limited on @%s (attempt %d/%d, retry in %.1fs)",
                            channel, attempt + 1, max_retries + 1, delay,
                        )
                        if attempt < max_retries:
                            await asyncio.sleep(delay)
                            continue
                        return []
                    resp.raise_for_status()
                    html = await resp.text()
                    break
            except (aiohttp.ClientError, asyncio.TimeoutError):
                if attempt < max_retries:
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                    logger.warning(
                        "Telegram fetch error for @%s (attempt %d/%d, retry in %.1fs)",
                        channel, attempt + 1, max_retries + 1, delay,
                    )
                    await asyncio.sleep(delay)
                    continue
                raise

        soup = BeautifulSoup(html, "html.parser")
        msg_wraps = soup.find_all(
            "div", class_=re.compile(r"tgme_widget_message_wrap")
        )

        messages: list[dict] = []
        for div in msg_wraps:
            inner = div.find(
                "div", class_=re.compile(r"tgme_widget_message\b")
            )
            data_post = inner.get("data-post") if inner else ""
            if not data_post:
                continue

            text_div = div.find(
                "div", class_=re.compile(r"tgme_widget_message_text")
            )
            text = ""
            if text_div:
                text = text_div.get_text(" ", strip=True)

            time_el = div.find("time")
            observed_at = None
            if time_el and time_el.get("datetime"):
                try:
                    observed_at = (
                        datetime.fromisoformat(time_el["datetime"])
                        .replace(tzinfo=None)
                    )
                except (ValueError, TypeError):
                    pass

            messages.append({
                "post": data_post,
                "text": text,
                "observed_at": observed_at,
            })

        return messages

    def _map_to_observation(
        self, msg: dict, channel: str
    ) -> Optional[Observation]:
        post = msg.get("post") or ""
        if not post:
            return None

        text = msg.get("text") or ""

        observation_type = _classify_message(text)

        coupon: Optional[str] = None
        if observation_type == ObservationType.COUPON:
            coupon = _extract_coupon_code(text)

        msg_id = post.split("/", 1)[-1] if "/" in post else post
        url = f"{TELEGRAM_WEB_BASE}/{channel}/{msg_id}"

        return Observation(
            source_id=self._source_id,
            external_id=post,
            observed_at=msg.get("observed_at") or datetime.utcnow(),
            observation_type=observation_type,
            title=text[:200] if text else None,
            url=url,
            raw_content=text[:5000] if text else None,
            coupon=coupon,
        )
