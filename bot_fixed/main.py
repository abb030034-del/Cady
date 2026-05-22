import asyncio
import logging
import os
import glob
from aiohttp import web

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("main")

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

from config import Client

for f in glob.glob("my_bot*"):
    try:
        os.remove(f)
    except Exception:
        pass

_bot_ready: bool = False


async def _health(request):
    if _bot_ready:
        return web.Response(text="✅ Bot is running", status=200)
    return web.Response(text="⏳ Bot is starting...", status=503)

async def _start_health_server():
    port = int(os.environ.get("PORT", 10000))
    app  = web.Application()
    app.router.add_get("/", _health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info("Health-check server on port %d", port)


async def _preload_games_data():
    """يُحمِّل بيانات الألعاب في الخلفية عند الإقلاع"""
    try:
        import importlib
        await asyncio.get_running_loop().run_in_executor(
            None, importlib.import_module, "helpers.games_data"
        )
        logger.info("بيانات الألعاب جاهزة ✅")
    except Exception as e:
        logger.warning("تعذّر تحميل بيانات الألعاب: %s", e)


async def _warm_up_cache():
    """
    ✅ إصلاح الأداء: تسخين كاش المجموعات المفعّلة عند الإقلاع
    يمنع أول رسالة من كل مجموعة من اللجوء إلى Redis الزامن
    """
    try:
        from config import ar, DEV_ID
        from helpers.utils import _utils_cache, _utils_cache_order, _utils_cache_cleanup
        import time

        groups = await ar.smembers(f"enablelist:{DEV_ID}")
        now = time.monotonic()
        for cid in groups:
            key = f"{cid}:enable:{DEV_ID}"
            _utils_cache[key] = (True, now, 30)
            _utils_cache_order.append(key)
        logger.info("تم تسخين كاش %d مجموعة ✅", len(groups))
    except Exception as e:
        logger.warning("تعذّر تسخين الكاش: %s", e)


async def main():
    from Plugins.auto_clean import _auto_clean_loop
    import Plugins.private_sudos as _ps

    await _start_health_server()

    async with Client:
        global _bot_ready
        me = await Client.get_me()
        _bot_ready = True
        logger.info("البوت شغال: @%s", me.username)

        _running_loop = asyncio.get_running_loop()

        # تسخين الكاش فوراً عند الإقلاع
        _running_loop.create_task(_warm_up_cache())
        _running_loop.create_task(_auto_clean_loop(Client))
        _running_loop.create_task(_preload_games_data())

        logger.info("جميع المهام الخلفية تعمل ✅")

        try:
            await asyncio.sleep(float("inf"))
        finally:
            await _ps._http.aclose()
            import Plugins.downloader as _dl
            await _dl._http.aclose()
            logger.info("تم إغلاق httpx clients")


if __name__ == "__main__":
    loop.run_until_complete(main())
