import asyncio

import pytest

from app.collectors.base import BaseCollector
from app.domain.entities import Observation, ObservationType


class DummyCollector(BaseCollector):
    def __init__(self, name="dummy", interval_seconds=1,
                 return_observations=None, raise_on_collect=False):
        super().__init__(name, interval_seconds)
        self.collect_calls = 0
        self._return_observations = return_observations or []
        self._raise_on_collect = raise_on_collect

    async def collect(self):
        self.collect_calls += 1
        if self._raise_on_collect:
            raise RuntimeError("simulated error")
        return self._return_observations


@pytest.mark.asyncio
async def test_collector_start_stop():
    collector = DummyCollector()
    await collector.start()
    assert collector._running is True
    assert collector._task is not None
    await asyncio.sleep(0.1)
    await collector.stop()
    assert collector._running is False


@pytest.mark.asyncio
async def test_collect_callback_invoked():
    observations = [
        Observation(observation_type=ObservationType.POST, title="test"),
    ]
    received = []

    async def callback(obs_list):
        received.extend(obs_list)

    collector = DummyCollector(return_observations=observations)
    collector.set_callback(callback)
    await collector.start()
    await asyncio.sleep(0.2)
    await collector.stop()

    assert len(received) >= 1
    assert received[0].title == "test"


@pytest.mark.asyncio
async def test_collect_error_does_not_crash():
    collector = DummyCollector(raise_on_collect=True)
    await collector.start()
    await asyncio.sleep(0.2)
    assert collector._running is True
    await collector.stop()


@pytest.mark.asyncio
async def test_collect_called_repeatedly():
    collector = DummyCollector(interval_seconds=0.05)
    await collector.start()
    await asyncio.sleep(0.2)
    await collector.stop()
    assert collector.collect_calls >= 2
