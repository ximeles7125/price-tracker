#!/usr/bin/env python
"""
Запуск Telegram-бота на aiogram.
Использование: python run_bot.py
"""

import os
import sys
import asyncio
import django

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

django.setup()

# Теперь можно импортировать бота
from tracker.bot.main import main as run_bot

if __name__ == '__main__':
    print("🤖 Запуск Telegram-бота на aiogram...")
    print("Нажми Ctrl+C для остановки")
    print("-" * 50)

    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        print("\n👋 Бот остановлен")