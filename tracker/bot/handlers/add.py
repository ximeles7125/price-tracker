"""
Обработчики для добавления товара (FSM: машина состояний)
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
router = Router(name="add")


# === Машина состояний ===
class AddProduct(StatesGroup):
    waiting_for_url = State()
    waiting_for_price = State()


# === Кнопка "➕ Добавить товар" ===
@router.message(F.text == "➕ Добавить товар")
async def start_add_product(message: types.Message, state: FSMContext):
    """Начинает процесс добавления товара"""
    await state.set_state(AddProduct.waiting_for_url)

    instruction = (
        f"➕ <b>Добавление товара</b>\n\n"
        f"Отправь мне ссылку на товар с Wildberries.\n"
        f"Пример: https://www.wildberries.ru/catalog/12345678/detail.aspx\n\n"
        f"Или нажми «❌ Отменить», чтобы вернуться в меню."
    )

    await message.answer(
        instruction,
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard()
    )


# === Получение URL ===
@router.message(AddProduct.waiting_for_url, F.text != "❌ Отменить")
async def process_url(message: types.Message, state: FSMContext):
    """Получает и проверяет URL"""
    user_input = message.text.strip()

    # Проверка: должна быть ссылка на Wildberries
    if 'wildberries' not in user_input.lower():
        await message.answer(
            "❌ Это не похоже на ссылку Wildberries.\n"
            "Пожалуйста, отправь корректную ссылку или нажми «❌ Отменить».",
            reply_markup=get_cancel_keyboard()
        )
        return

    # Сохраняем URL в state
    await state.update_data(product_url=user_input)

    # Запрашиваем цену
    price_instruction = (
        f"✅ Ссылка принята!\n\n"
        f"Теперь напиши желаемую цену в рублях (только число):\n"
        f"Пример: 5000 или 4999.99\n\n"
        f"Или нажми «❌ Отменить»."
    )

    await state.set_state(AddProduct.waiting_for_price)
    await message.answer(price_instruction, reply_markup=get_cancel_keyboard())


# === Получение цены и создание товара ===
@router.message(AddProduct.waiting_for_price, F.text != "❌ Отменить")
async def process_price(message: types.Message, state: FSMContext):
    """Получает цену, создаёт товар в БД"""
    user_input = message.text.strip()

    # Проверка: должно быть число
    try:
        target_price = float(user_input.replace(',', '.'))
        if target_price <= 0:
            raise ValueError
    except ValueError:
        await message.answer(
            "❌ Пожалуйста, введи корректное число (например, 5000 или 4999.99)\n"
            "Или нажми «❌ Отменить».",
            reply_markup=get_cancel_keyboard()
        )
        return

    # Показываем, что обрабатываем
    await message.answer("⏳ Обрабатываю...")

    # Получаем данные из state
    data = await state.get_data()
    product_url = data.get('product_url')
    telegram_id = message.from_user.id

    logger.info(f"🔍 Создаём товар: User={telegram_id}, URL={product_url}, Price={target_price}")

    try:
        # Создаём товар через sync_to_async
        product = await sync_to_async(Product.objects.create)(
            url=product_url,
            name="Товар из бота",  # Можно добавить парсинг названия позже
            target_price=target_price,
            telegram_id=telegram_id,
            is_active=True
        )

        logger.info(f"✅ Товар создан: ID={product.id}")

        # Подтверждение
        success_message = (
            f"✅ <b>Товар добавлен!</b>\n\n"
            f"🛍️ Товар из бота\n"
            f"🎯 Желаемая цена: {target_price:.2f} ₽\n"
            f"🔔 Ты получишь уведомление, когда цена упадёт!\n\n"
            f"Используй меню ниже для управления."
        )

        await message.answer(
            success_message,
            parse_mode="HTML",
            reply_markup=get_main_keyboard()
        )

    except Exception as e:
        logger.error(f"❌ Ошибка: {type(e).__name__}: {e}")
        await message.answer(
            f"❌ <b>Ошибка при добавлении товара!</b>\n\n"
            f"Попробуй ещё раз: нажми ➕ Добавить товар",
            parse_mode="HTML",
            reply_markup=get_main_keyboard()
        )
    finally:
        # Очищаем state
        await state.clear()


# === Отмена ===
@router.message(F.text == "❌ Отменить", StateFilter(AddProduct.waiting_for_url, AddProduct.waiting_for_price))
async def cancel_add_product(message: types.Message, state: FSMContext):
    """Отменяет добавление товара"""
    await state.clear()
    await message.answer(
        "❌ Действие отменено. Используй меню ниже, чтобы начать заново.",
        reply_markup=get_main_keyboard()
    )