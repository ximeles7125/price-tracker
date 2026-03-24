from celery import shared_task
from .models import Product
from .parsers.wb import parse_wildberries
from .telegram_bot import send_price_alert
import asyncio

@shared_task
def check_prices_task():
    # Берем только активные товары
    products = Product.objects.filter(is_active=True)

    for product in products:
        if 'wildberries' in product.url:
            new_price, name = parse_wildberries(product.url)

            if new_price:
                # Обновляем название, если оно пустое
                if not product.name and name:
                    product.name = name

                old_price = product.current_price
                product.current_price = new_price

                # Проверка условия
                if new_price <= product.target_price:
                    # Отправляем уведомление
                    asyncio.run(send_price_alert(
                        product.telegram_id,
                        product.name,
                        old_price,
                        new_price,
                        product.url
                    ))
                    # Опционально можно отключить товар чтобы не спамить
                    # product.is_active = False

                product.save()

