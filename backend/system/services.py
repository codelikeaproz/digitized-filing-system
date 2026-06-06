"""Helpers for reading system settings with simple process-level caching."""
from django.core.cache import cache

from orgunits.storage import BYTES_PER_MB

from .models import SystemSettings

CACHE_KEY = "system_settings_singleton"
CACHE_TTL_SECONDS = 60


def invalidate_system_settings_cache():
    cache.delete(CACHE_KEY)


def get_system_settings():
    cached = cache.get(CACHE_KEY)
    if cached is not None:
        return cached
    settings = SystemSettings.load()
    cache.set(CACHE_KEY, settings, CACHE_TTL_SECONDS)
    return settings


def get_upload_limit_bytes():
    return get_system_settings().upload_limit_mb * BYTES_PER_MB


def get_storage_quota_mb():
    return get_system_settings().storage_quota_mb
