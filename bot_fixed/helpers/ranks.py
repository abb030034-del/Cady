"""
نظام الرتب - يحدد صلاحيات كل مستخدم
الرتب من الأعلى للأدنى:
  مطور (DEV_ID) > مالك البوت (botowner) > Dev² > Myth > مالك أساسي > مالك > مدير > ادمن > مميز > عضو

✅ إصلاح كامل للأداء:
  - أول مرة: إرجاع قيمة افتراضية + تحديث async في الخلفية (لا blocking)
  - كاش TTL 8 ثانية مع stale-while-revalidate
  - حد أقصى 20,000 إدخال مع LRU eviction
  - is_locked مع كاش 30 ثانية
"""

import time
import asyncio
import logging
from config import r, ar, DEV_ID, DEV_ID_INT

logger = logging.getLogger("helpers.ranks")

_rank_cache: dict = {}
_rank_cache_order: list = []
_lock_cache: dict = {}
_lock_cache_order: list = []
_RANK_TTL = 8
_LOCK_TTL = 30
_MAX_RANK_CACHE = 20000
_MAX_LOCK_CACHE = 5000


def _rank_cache_cleanup():
    if len(_rank_cache) < _MAX_RANK_CACHE:
        return
    now = time.monotonic()
    expired = [k for k, (_, t) in _rank_cache.items() if now - t > _RANK_TTL]
    for k in expired:
        _rank_cache.pop(k, None)
        try: _rank_cache_order.remove(k)
        except ValueError: pass
    evict_count = max(0, len(_rank_cache) - int(_MAX_RANK_CACHE * 0.8))
    for k in _rank_cache_order[:evict_count]:
        _rank_cache.pop(k, None)
    del _rank_cache_order[:evict_count]


def _lock_cache_cleanup():
    if len(_lock_cache) < _MAX_LOCK_CACHE:
        return
    now = time.monotonic()
    expired = [k for k, (_, t) in _lock_cache.items() if now - t > _LOCK_TTL]
    for k in expired:
        _lock_cache.pop(k, None)
        try: _lock_cache_order.remove(k)
        except ValueError: pass
    evict_count = max(0, len(_lock_cache) - int(_MAX_LOCK_CACHE * 0.8))
    for k in _lock_cache_order[:evict_count]:
        _lock_cache.pop(k, None)
    del _lock_cache_order[:evict_count]


def _compute_level(su: str, vals) -> int:
    owner_id, rank_dev2, rank_dev, rank_go, rank_ow, rank_mo, rank_adm, rank_pre = vals
    if su == str(DEV_ID):           return 9
    if owner_id and su == owner_id: return 8
    if rank_dev2: return 7
    if rank_dev:  return 6
    if rank_go:   return 5
    if rank_ow:   return 4
    if rank_mo:   return 3
    if rank_adm:  return 2
    if rank_pre:  return 1
    return 0


def _get_rank_keys(su: str, sc: str) -> list:
    return [
        f"{DEV_ID}:owner",
        f"{su}:rankDEV2:{DEV_ID}",
        f"{su}:rankDEV:{DEV_ID}",
        f"{sc}:rankGOWNER:{su}:{DEV_ID}",
        f"{sc}:rankOWNER:{su}:{DEV_ID}",
        f"{sc}:rankMOD:{su}:{DEV_ID}",
        f"{sc}:rankADMIN:{su}:{DEV_ID}",
        f"{sc}:rankPRE:{su}:{DEV_ID}",
    ]


async def _refresh_rank_level(uid: int, cid: int):
    su, sc = str(uid), str(cid)
    try:
        vals = await ar.mget(_get_rank_keys(su, sc))
        level = _compute_level(su, vals)
    except Exception as e:
        logger.error("aget_user_level error uid=%s cid=%s: %s", uid, cid, e)
        return
    _rank_cache_cleanup()
    cache_key = (uid, cid)
    _rank_cache[cache_key] = (level, time.monotonic())
    try: _rank_cache_order.remove(cache_key)
    except ValueError: pass
    _rank_cache_order.append(cache_key)


def _get_rank_level(uid: int, cid: int) -> int:
    now = time.monotonic()
    cache_key = (uid, cid)
    entry = _rank_cache.get(cache_key)

    if entry:
        level, ts = entry
        if now - ts < _RANK_TTL:
            return level
        # الكاش انتهى — أعِد القيمة القديمة + حدّث في الخلفية (لا blocking)
        try:
            asyncio.get_running_loop().create_task(_refresh_rank_level(uid, cid))
        except RuntimeError:
            pass
        return level

    # أول مرة — إرجاع مبدئي فوري + تحديث async في الخلفية
    su = str(uid)
    level = 9 if su == str(DEV_ID) else 0

    _rank_cache_cleanup()
    _rank_cache[cache_key] = (level, now - _RANK_TTL + 1)  # ثانية واحدة فقط
    try: _rank_cache_order.remove(cache_key)
    except ValueError: pass
    _rank_cache_order.append(cache_key)

    try:
        asyncio.get_running_loop().create_task(_refresh_rank_level(uid, cid))
    except RuntimeError:
        # لا event loop — اجلب متزامن مرة واحدة فقط عند الإقلاع
        try:
            sc = str(cid)
            vals = r.mget(_get_rank_keys(su, sc))
            level = _compute_level(su, vals)
            _rank_cache[cache_key] = (level, time.monotonic())
        except Exception as e:
            logger.error("get_user_level sync error uid=%s cid=%s: %s", uid, cid, e)
    return level


def rank_cache_invalidate(uid: int, cid: int):
    k = (uid, cid)
    _rank_cache.pop(k, None)
    try: _rank_cache_order.remove(k)
    except ValueError: pass


# ── أسماء الرتب مع كاش 60 ثانية ────────────────────────────────────────

def get_rank(uid: int, cid: int) -> str:
    su, sc = str(uid), str(cid)
    level = _get_rank_level(uid, cid)

    _names_key = f"ranknames:{sc}:{su}"
    _names_now = time.monotonic()
    _names_entry = _rank_cache.get(_names_key)
    if _names_entry and _names_now - _names_entry[1] < 60:
        vals = _names_entry[0]
    else:
        try:
            all_keys = [
                f"{DEV_ID}:rankName:dev",
                f"{DEV_ID}:rankName:owner_g",
                f"{DEV_ID}:rankName:dev2",
                f"{DEV_ID}:rankName:myth",
                f"{sc}:RankGowner:{DEV_ID}",
                f"{sc}:RankOwner:{DEV_ID}",
                f"{sc}:RankMod:{DEV_ID}",
                f"{sc}:RankAdm:{DEV_ID}",
                f"{sc}:RankPre:{DEV_ID}",
                f"{sc}:RankMem:{DEV_ID}",
                f"{su}:gban:{DEV_ID}",
                f"{su}:mute:{DEV_ID}",
            ]
            vals = r.mget(all_keys)
            _rank_cache_cleanup()
            _rank_cache[_names_key] = (vals, _names_now)
            try: _rank_cache_order.remove(_names_key)
            except ValueError: pass
            _rank_cache_order.append(_names_key)
        except Exception as e:
            logger.error("get_rank_title error uid=%s cid=%s: %s", uid, cid, e)
            vals = [None] * 12

    if level == 9: return vals[0] or "مطوّر 🎖️"
    if level == 8: return vals[1] or "مالك البوت 🎖️"
    if vals[10]:   return "محظور عام 🔴"
    if vals[11]:   return "مكتوم عام 🔇"
    if level == 7: return vals[2] or "Dev²🎖"
    if level == 6: return vals[3] or "Myth🎖️"
    if level == 5: return vals[4] or "المالك الأساسي 👑"
    if level == 4: return vals[5] or "المالك 💎"
    if level == 3: return vals[6] or "المدير ⚙️"
    if level == 2: return vals[7] or "ادمن 🛡️"
    if level == 1: return vals[8] or "مميز ⭐"
    return vals[9] or "عضو"


def get_devs() -> list:
    try:
        devs = r.smembers(f"{DEV_ID}:DEVs") or set()
        return list(devs) + [str(DEV_ID)]
    except Exception:
        return [str(DEV_ID)]


# ── فحص الصلاحيات ────────────────────────────────────────────────────────

def is_dev(uid: int, cid: int = 0) -> bool:      return _get_rank_level(uid, cid) >= 9
def is_botowner(uid: int, cid: int = 0) -> bool: return _get_rank_level(uid, cid) >= 8
def is_dev2(uid: int, cid: int = 0) -> bool:     return _get_rank_level(uid, cid) >= 7
def is_myth(uid: int, cid: int = 0) -> bool:     return _get_rank_level(uid, cid) >= 6
def is_gowner(uid: int, cid: int) -> bool:       return _get_rank_level(uid, cid) >= 5
def is_owner(uid: int, cid: int) -> bool:        return _get_rank_level(uid, cid) >= 4
def is_mod(uid: int, cid: int) -> bool:          return _get_rank_level(uid, cid) >= 3
def is_admin(uid: int, cid: int) -> bool:        return _get_rank_level(uid, cid) >= 2
def is_pre(uid: int, cid: int) -> bool:          return _get_rank_level(uid, cid) >= 1

# aliases
def admin_pls(uid, cid):  return is_admin(uid, cid)
def mod_pls(uid, cid):    return is_mod(uid, cid)
def owner_pls(uid, cid):  return is_owner(uid, cid)
def gowner_pls(uid, cid): return is_gowner(uid, cid)
def dev_pls(uid, cid):    return is_myth(uid, cid)
def dev2_pls(uid, cid):   return is_dev2(uid, cid)
def devp_pls(uid, cid):   return is_botowner(uid, cid)
def pre_pls(uid, cid):    return is_pre(uid, cid)


# ── قفل الأوامر مع كاش ──────────────────────────────────────────────────

LOCK_LEVELS = {0: is_gowner, 1: is_owner, 2: is_mod, 3: is_admin, 4: is_pre}


def is_locked(uid: int, cid: int, text: str) -> bool:
    now = time.monotonic()
    cache_key = f"locks:{cid}"
    entry = _lock_cache.get(cache_key)
    if entry and now - entry[1] < _LOCK_TTL:
        locks = entry[0]
    else:
        try:
            locks = r.hgetall(f"{DEV_ID}:locks:{cid}")
        except Exception:
            locks = {}
        _lock_cache_cleanup()
        _lock_cache[cache_key] = (locks, now)
        try: _lock_cache_order.remove(cache_key)
        except ValueError: pass
        _lock_cache_order.append(cache_key)

    if not locks:
        return False
    level = locks.get(text)
    if level is None:
        return False
    check_fn = LOCK_LEVELS.get(int(level))
    return check_fn is not None and not check_fn(uid, cid)


def isLockCommand(uid: int, cid: int, text: str) -> bool:
    return is_locked(uid, cid, text)
