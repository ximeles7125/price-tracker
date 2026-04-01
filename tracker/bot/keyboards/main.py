"""
Клавиатуры для бота.
"""

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Главное меню с кнопками."""
    keyboard = [
        [KeyboardButton(text="➕ Добавить товар")],
        [KeyboardButton(text="📋 Мои товары")],
        [KeyboardButton(text="🗑️ Удалить товар")],
        [KeyboardButton(text="❓ Помощь")],
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="Выбери действие..."
    )


def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура с кнопкой отмены."""
    keyboard = [
        [KeyboardButton(text="❌ Отменить")],
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder="Нажми для отмены..."
    )