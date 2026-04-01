"""
Обработчики для удаления товара (FSM)
"""

import logging
from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import StateFilter
from asgiref.sync import sync_to_async

from tracker.models import Product
from tracker.bot.keyboards.main import get_main_keyboard, get_cancel_keyboard

logger = logging.getLogger(__name__)
router = Router(name="delete")


# === Машина состояний ===
class DeleteProduct(StatesGroup):
    waiting_for_selection = State()


# === Кнопка "🗑️ Удалить товар" ===
@router.message(F.text == "🗑️ Удалить товар")
async def start_delete_product(message: types.Message, state: FSMContext):
    """Показывает список товаров для удаления"""
    telegram_id = message.from_user.id

    # Запрос к БД
    products = await sync_to_async(list)(
        Product.objects.filter(
            telegram_id=telegram_id,
            is_active=True
        ).order_by('-created_at')[:10]
    )

    if not products:
        await message.answer(
            "📭 У тебя нет отслеживаемых товаров.\n"
            "Добавь первый: нажми ➕ Добавить товар",
            reply_markup=get_main_keyboard()
        )
        return

    # Формируем список
    text = f"🗑️ <b>Удаление товара</b>\n\n"
    text += f"Выбери номер товара для удаления:\n\n"

    for i, p in enumerate(products, 1):
        price_info = f"{p.current_price or '?'} ₽" if p.current_price else "ещё не проверено"
        text += f"<b>{i}.</b> {p.name or 'Без названия'}\n"
        text += f"   💰 {price_info} | 🎯 {p.target_price} ₽\n"
        text += f"   🔗 {p.url[:50]}...\n\n"

    text += f"<i>Напиши номер (1-{len(products)}) или «❌ Отменить»</i>"

    # Сохраняем товары в state
    await state.update_data(products_to_delete=[p.id for p in products])
    await state.set_state(DeleteProduct.waiting_for_selection)

    await message.answer(
        text,
        parse_mode="HTML",
        disable_web_page_preview=True,
        reply_markup=get_cancel_keyboard()
    )


# === Обработка выбора номера ===
@router.message(DeleteProduct.waiting_for_selection, F.text != "❌ Отменить")
async def process_selection(message: types.Message, state: FSMContext):
    """Удаляет выбранный товар"""
    user_input = message.text.strip()

    # Проверка: должно быть число
    try:
        selection = int(user_input)
        data = await state.get_data()
        products_ids = data.get('products_to_delete', [])

        if not products_ids or selection < 1 or selection > len(products_ids):
            raise ValueError
    except ValueError:
        max_num = len(await state.get_value('products_to_delete') or [])
        await message.answer(
            f"❌ Пожалуйста, введи корректный номер от 1 до {max_num}\n"
            f"Или нажми «❌ Отменить».",
            reply_markup=get_cancel_keyboard()
        )
        return

    # Удаляем товар
    telegram_id = message.from_user.id
    products_ids = (await state.get_data()).get('products_to_delete', [])
    selected_id = products_ids[selection - 1]

    # Мягкое удаление
    await sync_to_async(
        lambda: Product.objects.filter(id=selected_id, telegram_id=telegram_id).update(is_active=False)
    )()

    # Считаем оставшиеся
    remaining = await sync_to_async(
        lambda: Product.objects.filter(telegram_id=telegram_id, is_active=True).count()
    )()

    # Подтверждение
    success_message = (
        f"✅ <b>Товар удалён из отслеживания!</b>\n\n"
        f"🗑️ Товар #{selected_id}\n"
        f"Осталось товаров: {remaining}\n"
        f"Используй меню ниже."
    )

    await message.answer(
        success_message,
        parse_mode="HTML",
        reply_markup=get_main_keyboard()
    )

    # Очищаем state
    await state.clear()


# === Отмена ===
@router.message(DeleteProduct.waiting_for_selection, F.text == "❌ Отменить")
async def cancel_delete_product(message: types.Message, state: FSMContext):
    """Отменяет удаление"""
    await state.clear()
    await message.answer(
        "❌ Действие отменено. Используй меню ниже, чтобы начать заново.",
        reply_markup=get_main_keyboard()
    )