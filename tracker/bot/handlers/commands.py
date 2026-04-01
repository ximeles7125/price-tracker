"""
Обработчики простых команд: /start, /my, /help
"""

import logging
from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from asgiref.sync import sync_to_async
from django.conf import settings

from tracker.models import Product
from tracker.bot.keyboards.main import get_main_keyboard

logger = logging.getLogger(__name__)
router = Router(name="commands")


@router.message(F.text == "/start")
async def cmd_start(message: types.Message):
    """Обработчик команды /start"""
    user = message.from_user
    welcome_text = (
        f"👋 Привет, {user.first_name or 'друг'}!\n\n"
        f"Я — бот для отслеживания цен на Wildberries.\n\n"
        f"📋 <b>Что я умею:</b>\n"
        f"• Добавлять товары для отслеживания\n"
        f"• Присылать уведомления, когда цена падает\n"
        f"• Показывать список твоих товаров\n\n"
        f"🚀 <b>Нажми на кнопку ниже, чтобы начать!</b>"
    )

    await message.answer(
        welcome_text,
        parse_mode="HTML",
        reply_markup=get_main_keyboard()
    )


@router.message(F.text == "📋 Мои товары")
async def show_my_products(message: types.Message):
    """Показывает список товаров пользователя"""
    telegram_id = message.from_user.id

    # Запрос к БД через sync_to_async
    products = await sync_to_async(list)(
        Product.objects.filter(
            telegram_id=telegram_id,
            is_active=True
        ).order_by('-created_at')[:10]
    )

    if not products:
        await message.answer(
            "📭 У тебя пока нет отслеживаемых товаров.\n"
            "Добавь первый: нажми ➕ Добавить товар",
            reply_markup=get_main_keyboard()
        )
        return

    # Формируем список
    text = f"📋 <b>Твои товары</b> ({len(products)}):\n\n"
    for i, p in enumerate(products, 1):
        price_info = f"{p.current_price or '?'} ₽" if p.current_price else "ещё не проверено"
        text += f"<b>{i}.</b> {p.name or 'Без названия'}\n"
        text += f"   💰 Сейчас: {price_info} | 🎯 Цель: {p.target_price} ₽\n"
        text += f"   🔗 <a href='{p.url}'>Открыть</a>\n\n"

    text += "<i>Чтобы удалить товар, нажми 🗑️ Удалить товар</i>"

    await message.answer(
        text,
        parse_mode="HTML",
        disable_web_page_preview=True,
        reply_markup=get_main_keyboard()
    )


@router.message(F.text == "❓ Помощь")
async def cmd_help(message: types.Message):
    """Показывает справку"""
    help_text = (
        "❓ <b>Справка по командам</b>\n\n"
        "/start — Приветствие и инструкция\n"
        "➕ Добавить товар — Добавить новый товар для отслеживания\n"
        "📋 Мои товары — Показать мои отслеживаемые товары\n"
        "🗑️ Удалить товар — Удалить товар из отслеживания\n"
        "❌ Отменить — Отменить текущее действие\n"
        "❓ Помощь — Эта справка\n\n"
        "💡 <b>Совет:</b> Можно просто отправить ссылку на товар — бот предложит добавить его!"
    )

    await message.answer(
        help_text,
        parse_mode="HTML",
        reply_markup=get_main_keyboard()
    )