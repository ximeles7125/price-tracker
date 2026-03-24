import telegram
from django.conf import settings

async def send_price_alert(telegram_id, product_name, old_price, new_price, url):
    bot = telegram.Bot(token=settings.TELEGRAM_BOT_TOKEN)

    message = (
        f"🔥 Цена упала!</b>\n\n"
        f"Товар: {product_name}\n"
        f"Было: {old_price} ₽\n"
        f"Стало: {new_price} ₽\n"
        f"🛒 <a href='{url}'>Перейти к покупке</a>"
    )

    await bot.send_message(chat_id=telegram_id, text=message, parse_mode='HTML')

    