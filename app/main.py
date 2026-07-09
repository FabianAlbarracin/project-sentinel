import asyncio
import logging
import signal

from app.collectors.reddit.collector import RedditCollector
from app.collectors.telegram.collector import (
    TelegramCollector,
    _parse_channels,
)
from app.collectors.woot.collector import WootCollector
from app.domain.services import Processor
from app.infrastructure.config import Settings
from app.infrastructure.database import Database
from app.infrastructure.heartbeat import HeartbeatScheduler, TelegramListener
from app.infrastructure.notifications import TelegramNotifier


logger = logging.getLogger(__name__)

db: Database
processor: Processor
settings: Settings
sources: dict
sources_by_id: dict = {}
notifier: TelegramNotifier
collectors: list = []


async def handle_observations(observations):
    max_per_cycle = getattr(settings, "max_observations_per_cycle", 500)
    if len(observations) > max_per_cycle:
        logger.warning(
            "Truncating %d observations to max %d",
            len(observations), max_per_cycle,
        )
        observations = observations[:max_per_cycle]

    stored = 0
    duplicates = 0
    failures = 0
    matches = 0
    notified = 0

    for obs in observations:
        try:
            if obs.external_id:
                exists = await db.observation_exists(
                    obs.source_id, obs.external_id
                )
                if exists:
                    duplicates += 1
                    continue

            obs_id = await db.insert_observation(obs)
            stored += 1
            logger.debug(
                "Observation stored id=%d type=%s title=%s",
                obs_id, obs.observation_type.value, obs.title,
            )

            watch_item_id = processor.match_observation(obs)
            if watch_item_id is None:
                continue

            matches += 1
            await db.update_observation_watch_item(obs_id, watch_item_id)
            already_notified = await db.notification_exists(obs_id)
            if already_notified:
                continue

            logger.info(
                "Match found: watch_item_id=%d for observation id=%d",
                watch_item_id, obs_id,
            )

            notif_id = await db.insert_notification(
                obs_id, "telegram", "SUCCESS",
            )

            if notifier is not None:
                source = sources_by_id.get(obs.source_id)
                source_name = source.name if source else "unknown"
                sent = await notifier.send(obs, source_name)
                if not sent:
                    await db.update_notification_status(
                        notif_id, "FAILED",
                    )
                else:
                    await db.update_notification_status(
                        notif_id, "SUCCESS",
                    )
                    notified += 1

        except Exception:
            failures += 1
            logger.warning(
                "Failed to process observation: source_id=%s external_id=%s",
                getattr(obs, "source_id", None),
                getattr(obs, "external_id", None),
                exc_info=True,
            )

    if stored or duplicates or matches or failures:
        logger.info(
            "Batch processed: %d stored, %d duplicates, "
            "%d matches, %d notified, %d failures",
            stored, duplicates, matches, notified, failures,
        )


async def main():
    global db, processor, settings, sources, sources_by_id, notifier

    settings = Settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)

    logger.info("Project Sentinel starting...")

    db = Database(settings.database_url)
    await db.connect()
    await db.init_schema()
    await db.seed_defaults()

    watch_terms = await db.load_watch_terms()
    sources = await db.load_sources()
    sources_by_id = {s.id: s for s in sources.values()}
    logger.info("Loaded %d sources, %d watch items with terms",
                 len(sources), len(watch_terms))

    processor = Processor(watch_terms)

    if settings.telegram_bot_token and settings.telegram_chat_id:
        notifier = TelegramNotifier(
            bot_token=settings.telegram_bot_token,
            chat_id=settings.telegram_chat_id,
        )
        logger.info("Telegram notifier configured")
    else:
        logger.warning("Telegram bot token or chat ID not set; notifications disabled")
        notifier = None

    if "woot" in sources and sources["woot"].enabled:
        if settings.woot_api_key:
            woot_collector = WootCollector(
                name="woot",
                interval_seconds=settings.woot_interval_seconds,
                source_id=sources["woot"].id,
                api_key=settings.woot_api_key,
            )
            woot_collector.set_callback(handle_observations)
            await woot_collector.start()
            collectors.append(woot_collector)
        else:
            logger.warning(
                "Woot source enabled but WOOT_API_KEY not set; skipping"
            )

    if "reddit" in sources and sources["reddit"].enabled:
        reddit_collector = RedditCollector(
            name="reddit",
            interval_seconds=settings.reddit_interval_seconds,
            source_id=sources["reddit"].id,
        )
        reddit_collector.set_callback(handle_observations)
        await reddit_collector.start()
        collectors.append(reddit_collector)

    if "telegram" in sources and sources["telegram"].enabled:
        telegram_channels = _parse_channels(settings.telegram_channels)
        if telegram_channels:
            telegram_collector = TelegramCollector(
                name="telegram",
                interval_seconds=settings.telegram_interval_seconds,
                source_id=sources["telegram"].id,
                channels=telegram_channels,
            )
            telegram_collector.set_callback(handle_observations)
            await telegram_collector.start()
            collectors.append(telegram_collector)
        else:
            logger.warning(
                "Telegram source enabled but TELEGRAM_CHANNELS "
                "not set; skipping"
            )

    stop_event = asyncio.Event()

    listener = None
    heartbeat_scheduler = None
    if notifier is not None:
        listener = TelegramListener(
            bot_token=settings.telegram_bot_token,
            chat_id=settings.telegram_chat_id,
            db=db,
            sources_by_id=sources_by_id,
            collectors=collectors,
        )
        await listener.start()

        heartbeat_scheduler = HeartbeatScheduler(
            notifier=notifier,
            db=db,
            heartbeat_hour_utc=settings.heartbeat_hour_utc,
            summary_hour_utc=settings.summary_hour_utc,
        )
        await heartbeat_scheduler.start()

    def _signal_handler():
        logger.info("Shutdown signal received")
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, _signal_handler)
        except NotImplementedError:
            pass

    await stop_event.wait()

    logger.info("Stopping collectors...")
    for c in collectors:
        await c.stop()

    if listener is not None:
        await listener.stop()
    if heartbeat_scheduler is not None:
        await heartbeat_scheduler.stop()

    await db.disconnect()
    logger.info("Project Sentinel stopped")


if __name__ == "__main__":
    asyncio.run(main())
