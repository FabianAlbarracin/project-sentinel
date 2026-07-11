import logging
import re
from decimal import Decimal
from typing import Optional

from telegram import Bot
from telegram.error import TelegramError

from app.domain.entities import Observation, ObservationType

logger = logging.getLogger(__name__)

_MARKDOWN_ESCAPE = re.compile(r"([_*\[\]()~`>#+\-=|{}.!\\])")

_SEPARATOR = "\u2500" * 15


class TelegramNotifier:
    def __init__(self, bot_token: str, chat_id: str):
        self._bot = Bot(token=bot_token)
        self._chat_id = chat_id

    async def send(
        self,
        observation: Observation,
        source_name: str,
    ) -> Optional[int]:
        text = self._build_message(observation, source_name)
        try:
            msg = await self._bot.send_message(
                chat_id=self._chat_id,
                text=text,
                parse_mode="MarkdownV2",
            )
            logger.info(
                "Notification sent via Telegram: observation_id=%s "
                "message_id=%d",
                observation.id,
                msg.message_id,
            )
            return msg.message_id
        except TelegramError as e:
            logger.warning(
                "Failed to send Telegram notification: "
                "observation_id=%s error=%s",
                observation.id,
                type(e).__name__,
            )
            return None

    def _build_message(
        self,
        observation: Observation,
        source_name: str,
    ) -> str:
        source_lower = source_name.lower() if source_name else ""
        source_display = source_name.capitalize() if source_name else "Unknown"

        if source_lower == "telegram":
            return self._format_telegram_msg(observation)

        obs_type = observation.observation_type
        if obs_type == ObservationType.PRODUCT:
            return self._format_product(observation, source_display)
        elif obs_type == ObservationType.COUPON:
            return self._format_coupon(observation, source_display)
        else:
            return self._format_post(observation, source_display)

    def _format_product(
        self, obs: Observation, source: str
    ) -> str:
        title = _escape(obs.title or "")
        parts = ["\U0001f4e6 Producto detectado", "", f"Fuente: {source}"]
        if title:
            parts.extend(["", "Producto:", title])
        if obs.price is not None:
            price = _format_price(obs.price)
            currency = obs.currency or ""
            parts.append(f"Precio: {_escape(price)} {currency}")
        if obs.url:
            url = _escape(obs.url)
            parts.extend(["", _SEPARATOR, "", f"\U0001f517 [Abrir publicacion]({url})"])
        return "\n".join(parts)

    def _format_coupon(
        self, obs: Observation, source: str
    ) -> str:
        title = _escape(obs.title or "")
        coupon = _escape(obs.coupon or "")
        parts = ["\U0001f39f Cupon detectado"]
        if coupon:
            parts.append(f"Codigo: {coupon}")
        parts.append(f"Fuente: {source}")
        if title:
            parts.extend(["", "Titulo:", title])
        if obs.url:
            url = _escape(obs.url)
            parts.extend(["", _SEPARATOR, "", f"\U0001f517 [Abrir publicacion]({url})"])
        return "\n".join(parts)

    def _format_post(
        self, obs: Observation, source: str
    ) -> str:
        title = _escape(obs.title or "")
        parts = [
            "\U0001f4ac Publicacion relevante",
            "",
            f"Fuente: {source}",
        ]
        if title:
            parts.extend(["", "Titulo:", title])
        if obs.url:
            url = _escape(obs.url)
            parts.extend(["", _SEPARATOR, "", f"\U0001f517 [Abrir publicacion]({url})"])
        return "\n".join(parts)

    def _format_telegram_msg(self, obs: Observation) -> str:
        channel = _extract_channel(obs.url) or "desconocido"
        channel = _escape(channel)
        title = _escape(obs.title or "")
        parts = ["\U0001f4e2 Mensaje relevante", "", f"Grupo: {channel}"]
        if title:
            parts.extend(["", "Mensaje:", title])
        if obs.url:
            url = _escape(obs.url)
            parts.extend(["", _SEPARATOR, "", f"\U0001f517 [Abrir mensaje]({url})"])
        return "\n".join(parts)


def _extract_channel(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    match = re.match(r"https?://t\.me/([^/]+)", url)
    return match.group(1) if match else None


def _escape(text: str) -> str:
    return _MARKDOWN_ESCAPE.sub(r"\\\1", text)


def _format_price(price: Decimal) -> str:
    formatted = f"{price:,.2f}"
    if "." in formatted:
        formatted = formatted.rstrip("0").rstrip(".")
    return formatted
