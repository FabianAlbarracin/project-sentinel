import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Optional

from app.domain.entities import Observation

logger = logging.getLogger(__name__)


class BaseCollector(ABC):
    def __init__(self, name: str, interval_seconds: int):
        self._name = name
        self._interval = interval_seconds
        self._task: Optional[asyncio.Task] = None
        self._running = False
        self._observations_callback = None

    @property
    def name(self) -> str:
        return self._name

    def set_callback(self, callback):
        self._observations_callback = callback

    async def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._poll_loop())
        logger.info("Collector '%s' started (interval=%ds)",
                     self._name, self._interval)

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Collector '%s' stopped", self._name)

    async def _poll_loop(self) -> None:
        while self._running:
            try:
                observations = await self.collect()
                if observations and self._observations_callback:
                    await self._observations_callback(observations)
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Error in collector '%s'", self._name)
            await asyncio.sleep(self._interval)

    @abstractmethod
    async def collect(self) -> list[Observation]:
        ...
