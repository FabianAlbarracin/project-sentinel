import asyncio
import logging
import sys
from datetime import datetime, timedelta, timezone

import asyncpg

from app.infrastructure.config import Settings

logger = logging.getLogger(__name__)

OBSERVATION_STALE_MINUTES = 180


async def check_health() -> bool:
    settings = Settings()

    try:
        conn = await asyncio.wait_for(
            asyncpg.connect(
                settings.database_url,
                timeout=5,
            ),
            timeout=8,
        )
    except Exception:
        logger.exception("Healthcheck failed: DB unreachable")
        return False

    try:
        row = await asyncio.wait_for(
            conn.fetchrow(
                "SELECT MAX(created_at) AS last_obs, COUNT(*) AS total "
                "FROM observations"
            ),
            timeout=5,
        )
    except Exception:
        logger.exception("Healthcheck failed: DB query error")
        await conn.close()
        return False

    await conn.close()

    total = row["total"] if row else 0
    last_obs = row["last_obs"] if row else None

    if total == 0:
        logger.info("Healthcheck OK: fresh install (0 observations)")
        return True

    if last_obs is not None:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        cutoff = now - timedelta(minutes=OBSERVATION_STALE_MINUTES)
        since_last = now - last_obs.replace(tzinfo=None)
        if last_obs.replace(tzinfo=None) >= cutoff:
            logger.info(
                "Healthcheck OK: %d obs total, last %.0fm ago",
                total,
                since_last.total_seconds() / 60,
            )
            return True
        else:
            logger.warning(
                "Healthcheck FAILED: last observation %.0fm ago (stale > %dm)",
                since_last.total_seconds() / 60,
                OBSERVATION_STALE_MINUTES,
            )
            return False

    return True


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s [%(levelname)s] healthcheck: %(message)s",
    )
    healthy = asyncio.run(check_health())
    sys.exit(0 if healthy else 1)
