from celery import shared_task
from django.utils import timezone
from .models import Product
from .services import update_product_price
from .telegram_bot import send_price_alert


@shared_task
def check_all_prices():
    """
    Задача Celery: проверяет цены всех активных товаров.
    Запускается по расписанию через Celery Beat.
    """
    print(f"🔄 [{timezone.now()}] Начинаем проверку цен...")

    # Берём только активные товары
    products = Product.objects.filter(is_active=True)
    total = products.count()

    if total == 0:
        print("ℹ️ Нет активных товаров для проверки")
        return

    print(f"📦 Найдено {total} товаров для проверки")

    success = 0
    alerted = 0

    for product in products:
        # Обновляем цену
        if update_product_price_local(product):
            success += 1

            # Проверяем, не достигли ли желаемой цены
            if product.current_price and product.current_price <= product.target_price:
                print(f"🔥 ВНИМАНИЕ: Цена {product.current_price} ₽ достигла желаемой {product.target_price} ₽!")

                # Отправляем уведомление
                if send_price_alert_sync(product):
                    alerted += 1
                    print(f"✅ Уведомление отправлено для товара {product.id}")
                else:
                    print(f"❌ Не удалось отправить уведомление для товара {product.id}")
            else:
                # Для отладки: показываем, почему уведомление НЕ отправлено
                if product.current_price:
                    print(
                        f"ℹ️ {product.name}: {product.current_price} ₽ < {product.target_price} ₽ (условие не выполнено)")
                else:
                    print(f"ℹ️ {product.name}: цена ещё не обновлена")

        # Небольшая задержка, чтобы не блокировали
        import time
        time.sleep(1)

    print(f"✅ Проверка завершена: обновлено {success}/{total}, уведомлений: {alerted}")
    return {'updated': success, 'alerted': alerted}


def update_product_price_local(product):
    """
    Локальная версия обновления (чтобы не импортировать services в task).
    """
    from .parsers.wb import parse_wildberries

    try:
        if 'wildberries' in product.url.lower():
            new_price, new_name = parse_wildberries(product.url)
        else:
            print(f"❌ Неизвестный маркетплейс: {product.url}")
            return False

        if new_price is not None:
            old_price = product.current_price
            product.current_price = new_price
            if new_name and not product.name:
                product.name = new_name
            product.save()

            print(f"✅ {product.name}: {old_price} → {new_price} ₽")
            return True
        return False
    except Exception as e:
        print(f"❌ Ошибка обновления {product.id}: {e}")
        return False


def send_price_alert_sync(product):
    """
    Синхронная обёртка для отправки уведомления.
    """
    import asyncio
    try:
        # Запускаем асинхронную функцию в синхронном контексте
        asyncio.run(send_price_alert(
            telegram_id=product.telegram_id,
            product_name=product.name or 'Товар',
            old_price=product.current_price,
            new_price=product.current_price,
            url=product.url
        ))
        return True
    except Exception as e:
        print(f"❌ Ошибка отправки уведомления: {e}")
        return False