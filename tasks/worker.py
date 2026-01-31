"""Huey task queue worker configuration."""

import logging
from urllib.parse import urlparse
from huey import MemoryHuey, RedisHuey
from app.config import settings

logger = logging.getLogger(__name__)


def _mask_redis_url(url: str) -> str:
    """Return Redis URL with password masked for safe logging."""
    parsed = urlparse(url)
    if parsed.password:
        masked_netloc = f"{parsed.username or ''}:****@{parsed.hostname}:{parsed.port or 6379}"
        return f"{parsed.scheme}://{masked_netloc}{parsed.path}"
    return f"{parsed.scheme}://{parsed.hostname}:{parsed.port or 6379}{parsed.path}"


# Use MemoryHuey only for local process execution (non-Docker)
# Use RedisHuey for development (Docker) and production
if settings.ENVIRONMENT == "local":
    huey = MemoryHuey('triage-hub', immediate=False)
    logger.info("⚙️ Using MemoryHuey for local execution (no Redis required)")
else:
    huey = RedisHuey(
        'triage-hub',
        url=settings.REDIS_URL
    )
    logger.info(f"⚙️ Using RedisHuey with Redis at {_mask_redis_url(settings.REDIS_URL)}")
