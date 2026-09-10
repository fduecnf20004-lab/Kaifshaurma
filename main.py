import asyncio
import logging

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, HOST, PORT
from handlers import router
from storage import storage


async def health_handler(
    request: web.Request,
) -> web.Response:
    return web.Response(
        text="Kaif Shaurma bot is running"
    )


async def start_web_server() -> web.AppRunner:
    app = web.Application()

    app.router.add_get(
        "/",
        health_handler,
    )

    app.router.add_get(
        "/health",
        health_handler,
    )

    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(
        runner,
        HOST,
        PORT,
    )

    await site.start()

    return runner


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format=(
            "%(asctime)s | "
            "%(levelname)s | "
            "%(name)s | "
            "%(message)s"
        ),
    )

    if not BOT_TOKEN:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN не установлен"
        )

    await storage.initialize()

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(
            parse_mode=ParseMode.MARKDOWN
        ),
    )

    dispatcher = Dispatcher(
        storage=MemoryStorage()
    )

    dispatcher.include_router(router)

    web_runner = await start_web_server()

    try:
        await bot.delete_webhook(
            drop_pending_updates=False
        )

        await dispatcher.start_polling(bot)

    finally:
        await web_runner.cleanup()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
