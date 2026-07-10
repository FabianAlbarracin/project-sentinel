import asyncio
import logging
from datetime import datetime, timezone

from telegram import Bot
from telegram.error import TelegramError

logger = logging.getLogger(__name__)


class TelegramListener:
    def __init__(
        self,
        bot_token: str,
        chat_id: str,
        db,
        sources_by_id: dict,
        collectors: list,
    ):
        self._bot = Bot(token=bot_token)
        self._chat_id = str(chat_id)
        self._db = db
        self._sources_by_id = sources_by_id
        self._collectors = collectors
        self._last_update_id: int = 0
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        self._task = asyncio.create_task(self._poll_loop())
        logger.info("Telegram listener started (commands: /status)")

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Telegram listener stopped")

    async def _poll_loop(self) -> None:
        while True:
            try:
                updates = await self._bot.get_updates(
                    offset=self._last_update_id + 1,
                    timeout=10,
                    allowed_updates=["message", "message_reaction"],
                )
                for update in updates:
                    self._last_update_id = max(
                        self._last_update_id, update.update_id
                    )

                    if update.message is not None:
                        await self._handle_message(update.message)

                    if update.message_reaction is not None:
                        await self._handle_reaction(update.message_reaction)
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Error in Telegram listener poll loop")

            await asyncio.sleep(10)

    async def _handle_message(self, msg) -> None:
        if msg is None or msg.text is None:
            return
        if str(msg.chat.id) != self._chat_id:
            return

        text = msg.text.strip()
        if text == "/status":
            response = await self._build_status()
            try:
                await self._bot.send_message(
                    chat_id=self._chat_id,
                    text=response,
                )
            except TelegramError:
                logger.warning(
                    "Failed to send /status response"
                )

    async def _handle_reaction(self, reaction) -> None:
        if str(reaction.chat.id) != self._chat_id:
            return

        notification = await self._db.find_notification_by_message_id(
            reaction.message_id,
        )
        if notification is None:
            return

        for r in reaction.new_reaction:
            emoji = getattr(r, "emoji", None)
            if emoji in ("\U0001f44d", "\U0001f44e"):
                await self._db.insert_feedback(
                    notification["id"], emoji,
                )
                logger.info(
                    "Feedback stored: notification_id=%d reaction=%s",
                    notification["id"], emoji,
                )

        try:
            await self._bot.send_message(
                chat_id=self._chat_id,
                text="Feedback recibido \u2713",
                reply_to_message_id=reaction.message_id,
            )
        except TelegramError:
            logger.warning("Failed to send feedback acknowledgment")

    async def _build_status(self) -> str:
        try:
            stats = await self._db.get_daily_stats()
        except Exception:
            logger.exception("Failed to fetch daily stats for /status")
            return "Error consultando estadisticas. Revisa los logs."

        now = datetime.utcnow()
        sources = stats.get("sources", {})
        latest_map = stats.get("latest", {})
        notified = stats.get("notified", 0)

        parts = ["\U0001f4e1 Sentinel online", ""]

        active = [c.name for c in self._collectors if c._running]
        parts.append(f"Collectors activos: {len(active)}/{len(self._collectors)}")
        for c in self._collectors:
            status_icon = "\u2705" if c._running else "\u274c"
            parts.append(f"  {status_icon} {c.name}")

        parts.append("")
        parts.append("Hoy:")
        for source_name in sorted(sources):
            data = sources[source_name]
            last = latest_map.get(source_name)
            ago = ""
            if last:
                delta = now - last.replace(tzinfo=None)
                if delta.total_seconds() < 3600:
                    ago = f" (ultima hace {int(delta.total_seconds() // 60)}m)"
                else:
                    ago = f" (ultima hace {int(delta.total_seconds() // 3600)}h)"
            parts.append(
                f"  {source_name}: {data['observations']} obs, {data['matches']} matches{ago}"
            )

        parts.append("")
        parts.append(f"Notificaciones enviadas hoy: {notified}")

        return "\n".join(parts)


class HeartbeatScheduler:
    def __init__(
        self,
        notifier,
        db,
        heartbeat_hour_utc: int = 14,
        summary_hour_utc: int = 3,
    ):
        self._notifier = notifier
        self._db = db
        self._heartbeat_hour = heartbeat_hour_utc
        self._summary_hour = summary_hour_utc
        self._sent_heartbeat: str | None = None
        self._sent_summary: str | None = None
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        self._task = asyncio.create_task(self._poll_loop())
        logger.info(
            "Heartbeat scheduler started (heartbeat=%d:00 UTC, summary=%d:00 UTC)",
            self._heartbeat_hour,
            self._summary_hour,
        )

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Heartbeat scheduler stopped")

    async def _poll_loop(self) -> None:
        while True:
            try:
                now = datetime.utcnow()
                today = now.strftime("%Y-%m-%d")
                hour = now.hour

                if (
                    hour == self._heartbeat_hour
                    and self._sent_heartbeat != today
                    and self._notifier is not None
                ):
                    msg = await self._build_heartbeat()
                    await self._notifier._bot.send_message(
                        chat_id=self._notifier._chat_id,
                        text=msg,
                    )
                    self._sent_heartbeat = today
                    logger.info("Heartbeat sent")

                elif (
                    hour == self._summary_hour
                    and self._sent_summary != today
                    and self._notifier is not None
                ):
                    msg = await self._build_summary()
                    await self._notifier._bot.send_message(
                        chat_id=self._notifier._chat_id,
                        text=msg,
                    )
                    self._sent_summary = today
                    logger.info("Daily summary sent")

            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Error in heartbeat scheduler")

            await asyncio.sleep(60)

    async def _build_heartbeat(self) -> str:
        try:
            stats = await self._db.get_daily_stats()
        except Exception:
            return "Sentinel heartbeat: error al consultar DB"

        sources = stats.get("sources", {})
        latest_map = stats.get("latest", {})
        now = datetime.utcnow()

        parts = ["\U0001f9ed Sentinel operativo", ""]

        for source_name in sorted(sources):
            last = latest_map.get(source_name)
            ago = "sin datos"
            if last:
                delta = now - last.replace(tzinfo=None)
                minutes = int(delta.total_seconds() // 60)
                if minutes < 60:
                    ago = f"hace {minutes}m"
                else:
                    ago = f"hace {minutes // 60}h {minutes % 60}m"
            parts.append(f"{source_name}: {ago}")

        parts.append("")
        notif_count = stats.get("notified", 0)
        if notif_count:
            parts.append(f"\U0001f514 {notif_count} notificaciones hoy")

        return "\n".join(parts)

    async def _build_summary(self) -> str:
        try:
            stats = await self._db.get_daily_stats()
        except Exception:
            return "Sentinel summary: error al consultar DB"

        sources = stats.get("sources", {})
        today = datetime.utcnow().strftime("%Y-%m-%d")

        parts = [f"\U0001f4ca Resumen {today}", ""]
        parts.append("Observaciones:")

        total_obs = 0
        total_matches = 0
        for source_name in sorted(sources):
            data = sources[source_name]
            obs = data["observations"]
            matches = data["matches"]
            total_obs += obs
            total_matches += matches
            parts.append(f"  {source_name}: {obs} obs, {matches} matches")

        parts.append("")
        parts.append(
            f"Total: {total_obs} observaciones, {total_matches} coincidencias"
        )

        notified = stats.get("notified", 0)
        errors = stats.get("errors", 0)
        parts.append(f"Notificaciones enviadas: {notified}")
        if errors:
            parts.append(f"Errores de envio: {errors}")

        return "\n".join(parts)
