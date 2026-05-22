"""
ملف الإعدادات — config.py
⚠️ قم بتعديل القيم أدناه قبل تشغيل البوت
"""

import os
import redis
import redis.asyncio as aioredis
import pyrogram
from pyrogram import Client as PyrogramClient

# ── إعدادات البوت الأساسية ────────────────────────────────────────────────
# احصل عليها من https://my.telegram.org/apps
API_ID   = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "YOUR_API_HASH")

# احصل على التوكن من @BotFather
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN")

# آيدي المطور الرئيسي (رقم)
DEV_ID     = int(os.environ.get("DEV_ID", "0"))
DEV_ID_INT = DEV_ID

# ── إعدادات Redis ─────────────────────────────────────────────────────────
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")

# Redis متزامن (للعمليات الأولى فقط — يُستخدم بحذر)
r = redis.from_url(REDIS_URL, decode_responses=True)

# Redis غير متزامن (الأساسي في جميع المعالجات)
ar = aioredis.from_url(REDIS_URL, decode_responses=True)

# ── الكاشات المحلية ───────────────────────────────────────────────────────
_smembers_cache: dict = {}

def cached_smembers(key: str, ttl: int = 60) -> set:
    """كاش محلي لـ smembers — يقلل طلبات Redis"""
    import time
    entry = _smembers_cache.get(key)
    if entry:
        val, ts = entry
        if time.monotonic() - ts < ttl:
            return val
    try:
        val = r.smembers(key)
    except Exception:
        val = set()
    _smembers_cache[key] = (val, time.monotonic())
    return val


def cache_invalidate_prefix(prefix: str):
    """امسح كاش smembers لمفتاح معين"""
    keys_to_del = [k for k in _smembers_cache if k.startswith(prefix)]
    for k in keys_to_del:
        _smembers_cache.pop(k, None)


# ── اسم البوت ورمزه (مع كاش TTL) ─────────────────────────────────────────
_botname_cache: tuple | None = None
_botkey_cache: tuple | None = None
_NAME_TTL = 60
_KEY_TTL  = 60

def botname() -> str:
    import time
    global _botname_cache
    if _botname_cache:
        val, ts = _botname_cache
        if time.monotonic() - ts < _NAME_TTL:
            return val
    val = r.get(f"{DEV_ID}:BotName") or "بوت"
    _botname_cache = (val, time.monotonic())
    return val

def botkey() -> str:
    import time
    global _botkey_cache
    if _botkey_cache:
        val, ts = _botkey_cache
        if time.monotonic() - ts < _KEY_TTL:
            return val
    val = r.get(f"{DEV_ID}:botkey") or "⚡"
    _botkey_cache = (val, time.monotonic())
    return val


# ── إنشاء Client ──────────────────────────────────────────────────────────
Client = PyrogramClient(
    "my_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    plugins={"root": "Plugins"},
    sleep_threshold=0,           # ✅ لا انتظار بين دورات الـ polling
    max_concurrent_transmissions=5,
)
