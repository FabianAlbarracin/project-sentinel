import asyncio
import logging
import random
import re
from datetime import datetime, timezone
from typing import Optional

import aiohttp
from bs4 import BeautifulSoup

from app.collectors.base import BaseCollector
from app.collectors.scoring import is_deal
from app.domain.entities import Observation, ObservationType


logger = logging.getLogger(__name__)

REDDIT_BASE = "https://old.reddit.com"
REDDIT_WEB_BASE = "https://www.reddit.com"
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

DEFAULT_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "User-Agent": "ProjectSentinel/1.0 (Reddit deal scraper)",
}

DEFAULT_SUBREDDITS = ["kindle", "ereader", "kindlescribe"]

COUPON_KEYWORDS = [
    "coupon", "coupon code", "discount code", "discount",
    "promo code", "promo", "deal", "% off", "$ off",
    "off code",
]

COUPON_CODE_RE = re.compile(
    r"\b([A-Z0-9]{5,20})\b",
)


def _is_deal_post(title: str) -> bool:
    return is_deal(title)

def _classify_post(title: str, selftext: str) -> ObservationType:
    combined = f"{title} {selftext}".lower()
    for kw in COUPON_KEYWORDS:
        if kw in combined:
            return ObservationType.COUPON
    return ObservationType.POST


def _extract_coupon_code(title: str, selftext: str) -> Optional[str]:
    combined = f"{title} {selftext}"
    matches = COUPON_CODE_RE.findall(combined)
    skip_words = {
        "TODAY", "TOMORROW", "LIMITED", "SUBSCRIBE", "PLEASE",
        "COMMENT", "REMEMBER", "AMAZON", "KINDLE", "PAPERWHITE",
        "THREAD", "HELLO", "CHECK", "HEADS", "SERIES", "MODEL",
        "EDITION", "DOESNT", "DOES", "USING", "WOULD", "THERE",
        "ABOUT", "BEFORE", "DURING", "AFTER", "REVIEW", "DONT",
    }
    for m in matches:
        if m not in skip_words and not re.fullmatch(r"\d+", m):
            return m
    return None


class RedditCollector(BaseCollector):
    def __init__(
        self,
        name: str,
        interval_seconds: int,
        source_id: int,
        subreddits: Optional[list[str]] = None,
    ):
        super().__init__(name, interval_seconds)
        self._source_id = source_id
        self._subreddits = subreddits or DEFAULT_SUBREDDITS
        self._session: Optional[aiohttp.ClientSession] = None

    async def start(self) -> None:
        self._session = aiohttp.ClientSession(headers=DEFAULT_HEADERS)
        await super().start()

    async def stop(self) -> None:
        if self._session:
            await self._session.close()
            self._session = None
        await super().stop()

    async def collect(self) -> list[Observation]:
        if not self._session:
            return []

        observations: list[Observation] = []
        total_fetched = 0

        for subreddit in self._subreddits:
            try:
                posts = await self._fetch_subreddit(subreddit)
                total_fetched += len(posts)
                for post in posts:
                    title = post.get("title", "")
                    if not _is_deal_post(title):
                        continue
                    obs = self._map_to_observation(post)
                    if obs:
                        observations.append(obs)
            except Exception:
                logger.exception("Failed to fetch r/%s", subreddit)

            if len(self._subreddits) > 1:
                await asyncio.sleep(random.uniform(1, 3))

        logger.info(
            "Reddit collect: %d observations (deal-filtered from %d posts) "
            "across %d subreddits",
            len(observations),
            total_fetched,
            len(self._subreddits),
        )
        return observations

    async def _fetch_subreddit(self, subreddit: str) -> list[dict]:
        url = f"{REDDIT_BASE}/r/{subreddit}/new/?limit=100"
        max_retries = 3
        base_delay = 5

        for attempt in range(max_retries + 1):
            try:
                async with self._session.get(url) as resp:
                    if resp.status == 429:
                        retry_after = resp.headers.get("Retry-After")
                        delay = float(retry_after) if retry_after else base_delay * (2 ** attempt) + random.uniform(0, 2)
                        logger.warning(
                            "Reddit rate limited on r/%s (attempt %d/%d, retry in %.1fs)",
                            subreddit, attempt + 1, max_retries + 1, delay,
                        )
                        if attempt < max_retries:
                            await asyncio.sleep(delay)
                            continue
                        return []
                    if resp.status == 404:
                        logger.warning("Subreddit r/%s not found", subreddit)
                        return []
                    resp.raise_for_status()
                    html = await resp.text()
                    break
            except (aiohttp.ClientError, asyncio.TimeoutError):
                if attempt < max_retries:
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                    logger.warning(
                        "Reddit fetch error for r/%s (attempt %d/%d, retry in %.1fs)",
                        subreddit, attempt + 1, max_retries + 1, delay,
                    )
                    await asyncio.sleep(delay)
                    continue
                raise

        soup = BeautifulSoup(html, "html.parser")
        things = soup.find_all("div", class_=re.compile(r"\bthing\b"))
        if not things:
            site_table = soup.find("div", id="siteTable")
            if site_table:
                things = site_table.find_all("div", class_=re.compile(r"\bthing\b"))

        posts: list[dict] = []
        for div in things:
            fullname = div.get("data-fullname")
            if not fullname or not fullname.startswith("t3_"):
                continue

            if "promoted" in div.get("class", []):
                continue

            post_data = {"id": fullname[3:], "title": "", "permalink": "", "observed_at": None}

            title_el = div.find("a", class_="title")
            if title_el:
                post_data["title"] = title_el.get_text(strip=True)

            permalink = div.get("data-permalink")
            if permalink:
                post_data["permalink"] = f"{REDDIT_WEB_BASE}{permalink}"

            time_el = div.find("time")
            if time_el and time_el.get("datetime"):
                try:
                    post_data["observed_at"] = (
                        datetime.fromisoformat(time_el["datetime"])
                        .replace(tzinfo=None)
                    )
                except (ValueError, TypeError):
                    pass

            posts.append(post_data)

        return posts

    def _map_to_observation(self, post: dict) -> Optional[Observation]:
        post_id = post.get("id")
        if not post_id:
            return None

        title = post.get("title") or ""
        permalink = post.get("permalink") or ""
        selftext = post.get("selftext") or ""

        observation_type = _classify_post(title, selftext)

        coupon: Optional[str] = None
        if observation_type == ObservationType.COUPON:
            coupon = _extract_coupon_code(title, selftext)

        return Observation(
            source_id=self._source_id,
            external_id=post_id,
            observed_at=post.get("observed_at") or datetime.utcnow(),
            observation_type=observation_type,
            title=title[:1000] if title else None,
            url=permalink or None,
            raw_content=title[:5000] if title else None,
            coupon=coupon,
        )
