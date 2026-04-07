from celery import shared_task
from django.utils import timezone
from django.conf import settings  # ← ← ← ДОБАВИТЬ ЭТУ СТРОКУ!
from .models import Product
from .services import update_product_price


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
    Локальная версия обновления цены.
    """
    from .parsers.wb import parse_wildberries_sync

    try:
        if 'wildberries' in product.url.lower():
            # API-парсер будет использован автоматически (use_api_first=True по умолчанию)
            # ✅ СТАЛО (правильно):
            new_price, new_name = parse_wildberries_sync(
                product.url,
                timeout=40  # ← Только timeout, без delay_range
            )
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

async def send_price_alert(telegram_id, product_name, old_price, new_price, url, product_id=None):
    """
    Отправляет уведомление о снижении цены через aiogram.
    Вызывается из send_price_alert_sync() через asyncio.run()
    """
    from aiogram import Bot
    from django.conf import settings
    import logging
    
    logger = logging.getLogger(__name__)
    
    token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
    if not token or not telegram_id:
        logger.error("❌ Bot token or telegram_id not found")
        return False
    
    bot = Bot(token=token)
    
    try:
        discount = old_price - new_price if old_price else 0
        discount_percent = (discount / old_price * 100) if old_price else 0
        
        emoji = "🔥" if product_id else "💸"
        id_marker = f" [ID:{product_id}]" if product_id else ""
        
        message = (
            f"{emoji} <b>Цена снизилась{id_marker}!</b>\n\n"
            f"🛍️ <b>{product_name}</b>\n"
            f"💰 Было: <s>{old_price} ₽</s>\n"
            f"💸 Стало: <b>{new_price} ₽</b>\n"
        )
        
        if discount > 0:
            message += f"📉 Экономия: {discount:.0f} ₽ ({discount_percent:.0f}%)\n"
        
        message += f"\n🛒 <a href='{url}'>Перейти к покупке</a>"
        
        await bot.send_message(chat_id=telegram_id, text=message, parse_mode='HTML')
        logger.info(f"✅ Alert sent to user {telegram_id}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error sending alert: {type(e).__name__}: {e}")
        return False
    finally:
        await bot.session.close()  # Важно: закрываем сессию!
