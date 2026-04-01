"""
Точка входа для Telegram-бота на aiogram.
Запуск: python -m tracker.bot.main
"""

import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from django.conf import settings

# Импортируем роутеры
from tracker.bot.handlers import commands, add, delete
from tracker.bot.keyboards import main  # Для регистрации клавиатур (опционально)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def on_startup(bot: Bot):
    """Выполняется при запуске бота"""
    logger.info(f"🤖 Бот запущен: @{(await bot.get_me()).username}")


async def on_shutdown(bot: Bot):
    """Выполняется при остановке бота"""
    logger.info("👋 Бот остановлен")
    await bot.session.close()


def create_dispatcher() -> Dispatcher:
    """Создаёт и настраивает Dispatcher"""
    token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN not found in settings")

    # Создаём бота
    bot = Bot(
        token=token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    # Создаём Dispatcher
    dp = Dispatcher(storage=MemoryStorage())

    # Регистрируем роутеры
    dp.include_router(commands.router)
    dp.include_router(add.router)
    dp.include_router(delete.router)

    # Регистрируем хуки
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    return dp, bot


async def main():
    """Главная функция запуска"""
    dp, bot = create_dispatcher()

    # Удаляем вебхук (для polling)
    await bot.delete_webhook(drop_pending_updates=True)

    logger.info("🚀 Запускаем polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    # Для запуска через python -m tracker.bot.main
    asyncio.run(main())