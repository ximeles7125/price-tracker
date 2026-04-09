from celery import shared_task
from django.utils import timezone
from django.conf import settings  # ← ← ← ДОБАВИТЬ ЭТУ СТРОКУ!
from .models import Product
from .services import update_product_price


# @shared_task
# def check_all_prices():
#     """
#     Задача Celery: проверяет цены всех активных товаров.
#     Запускается по расписанию через Celery Beat.
#     """
#     print(f"🔄 [{timezone.now()}] Начинаем проверку цен...")
#
#     # Берём только активные товары
#     products = Product.objects.filter(is_active=True)
#     total = products.count()
#
#     if total == 0:
#         print("ℹ️ Нет активных товаров для проверки")
#         return
#
#     print(f"📦 Найдено {total} товаров для проверки")
#
#     success = 0
#     alerted = 0
#
#     for product in products:
#         # Обновляем цену
#         if update_product_price_local(product):
#             success += 1
#
#             # Проверяем, не достигли ли желаемой цены
#             if product.current_price and product.current_price <= product.target_price:
#                 print(f"🔥 ВНИМАНИЕ: Цена {product.current_price} ₽ достигла желаемой {product.target_price} ₽!")
#
#                 # Отправляем уведомление
#                 if send_price_alert_sync(product):
#                     alerted += 1
#                     print(f"✅ Уведомление отправлено для товара {product.id}")
#                 else:
#                     print(f"❌ Не удалось отправить уведомление для товара {product.id}")
#             else:
#                 # Для отладки: показываем, почему уведомление НЕ отправлено
#                 if product.current_price:
#                     print(
#                         f"ℹ️ {product.name}: {product.current_price} ₽ < {product.target_price} ₽ (условие не выполнено)")
#                 else:
#                     print(f"ℹ️ {product.name}: цена ещё не обновлена")
#
#         # Небольшая задержка, чтобы не блокировали
#         import time
#         time.sleep(1)
#
#     print(f"✅ Проверка завершена: обновлено {success}/{total}, уведомлений: {alerted}")
#     return {'updated': success, 'alerted': alerted}

@shared_task
def check_all_prices():
    """
    Проверяет цены всех активных товаров и отправляет уведомления.
    """
    from tracker.models import Product
    from tracker.parsers.wb import parse_wildberries_sync
    from telegram_bot import bot

    logger.warning(f"🔄 [{datetime.now()}] Начинаем проверку цен...")

    products = Product.objects.filter(is_active=True)
    logger.warning(f"📦 Найдено {products.count()} товаров для проверки")

    updated_count = 0
    alerted_count = 0

    for product in products:
        try:
            # === 1. Сохраняем СТАРУЮ цену ДО обновления ===
            old_price = product.current_price  # ← Сохраняем ДО парсинга!

            # === 2. Парсим новую цену ===
            new_price, new_name = parse_wildberries_sync(product.url)

            if new_price is None:
                logger.warning(f"⚠️ Не удалось получить цену для {product.id}")
                continue

            # === 3. Обновляем товар в БД ===
            product.current_price = new_price
            if new_name and not product.name:
                product.name = new_name
            product.save()

            updated_count += 1
            logger.info(f"✅ {product.name[:40]}: {old_price} → {new_price} ₽")

            # === 4. Проверяем, нужно ли отправлять уведомление ===
            if product.telegram_id:
                should_notify = False

                # Уведомляем, если:
                # 1. Первая проверка (old_price was None)
                # 2. Цена снизилась
                # 3. Целевая цена достигнута

                if old_price is None:
                    should_notify = True
                elif new_price < old_price:
                    should_notify = True
                elif product.target_price and new_price <= product.target_price:
                    should_notify = True

                if should_notify:
                    # === 5. Отправляем уведомление ===
                    # Передаём СТАРУЮ и НОВУЮ цены правильно!
                    asyncio.run(send_price_alert(
                        telegram_id=product.telegram_id,
                        product_name=product.name or 'Товар',
                        old_price=old_price,  # ← Старая цена (до обновления)
                        new_price=new_price,  # ← Новая цена (после обновления)
                        url=product.url,
                        product_id=product.id,
                        target_price=product.target_price  # ← Целевая цена
                    ))
                    alerted_count += 1
                    logger.info(f"🔔 Уведомление отправлено в чат {product.telegram_id}")

        except Exception as e:
            logger.error(f"❌ Ошибка обновления {product.id}: {e}")
            continue

    logger.warning(f"✅ Проверка завершена: обновлено {updated_count}/{products.count()}, уведомлений: {alerted_count}")
    return {'updated': updated_count, 'alerted': alerted_count}


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


# def send_price_alert_sync(product):
#     """
#     Синхронная обёртка для отправки уведомления.
#     """
#     import asyncio
#     try:
#         # Запускаем асинхронную функцию в синхронном контексте
#         asyncio.run(send_price_alert(
#             telegram_id=product.telegram_id,
#             product_name=product.name or 'Товар',
#             old_price=product.current_price,
#             new_price=product.current_price,
#             url=product.url
#         ))
#         return True
#     except Exception as e:
#         print(f"❌ Ошибка отправки уведомления: {e}")
#         return False

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
            old_price=product.current_price,  # ← Старая цена (до обновления)
            new_price=product.current_price,  # ← Новая цена (после обновления)
            url=product.url,
            product_id=product.id,
            target_price=product.target_price  # ← ДОБАВИЛИ!
        ))
        return True
    except Exception as e:
        logger.error(f"❌ Error in send_price_alert_sync: {e}")
        return False
#
#
# async def send_price_alert(telegram_id, product_name, old_price, new_price, url, product_id=None):
#     """
#     Отправляет уведомление об изменении цены через aiogram.
#
#     Поддерживает три сценария:
#     • 📉 Цена снизилась — показываем экономию
#     • 📈 Цена выросла — показываем рост
#     • ➡️ Цена не изменилась — информируем
#     • 💰 Первая проверка — показываем новую цену
#
#     Вызывается из send_price_alert_sync() через asyncio.run()
#     """
#     from aiogram import Bot
#     from django.conf import settings
#     import logging
#     from datetime import datetime
#
#     logger = logging.getLogger(__name__)
#
#     token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
#     if not token or not telegram_id:
#         logger.error("❌ Bot token or telegram_id not found")
#         return False
#
#     bot = Bot(token=token)
#
#     try:
#         # === Формируем заголовок и эмодзи в зависимости от изменения цены ===
#         if old_price is None:
#             # Первая проверка цены
#             emoji = "💰"
#             title = "Первая проверка цены!"
#             price_block = f"💸 Новая цена: <b>{new_price:,.2f} ₽</b>"
#         elif new_price < old_price:
#             # Цена снизилась 📉
#             discount = old_price - new_price
#             discount_percent = (discount / old_price * 100) if old_price > 0 else 0
#             emoji = "📉"
#             title = "Цена снизилась!"
#             price_block = (
#                 f"💰 Было: <s>{old_price:,.2f} ₽</s>\n"
#                 f"💸 Стало: <b>{new_price:,.2f} ₽</b>\n"
#                 f"🎁 Экономия: <b>{discount:,.0f} ₽</b> ({discount_percent:.0f}%)"
#             )
#         elif new_price > old_price:
#             # Цена выросла 📈
#             increase = new_price - old_price
#             increase_percent = (increase / old_price * 100) if old_price > 0 else 0
#             emoji = "📈"
#             title = "Цена выросла"
#             price_block = (
#                 f"💰 Было: <s>{old_price:,.2f} ₽</s>\n"
#                 f"💸 Стало: <b>{new_price:,.2f} ₽</b>\n"
#                 f"🔼 Рост: <b>{increase:,.0f} ₽</b> ({increase_percent:.0f}%)"
#             )
#         else:
#             # Цена не изменилась ➡️
#             emoji = "➡️"
#             title = "Цена не изменилась"
#             price_block = f"💰 Цена: <b>{new_price:,.2f} ₽</b>"
#
#         # === ID товара (опционально) ===
#         id_marker = f" [ID:{product_id}]" if product_id else ""
#
#         # === Формируем основное сообщение ===
#         message = (
#             f"{emoji} <b>{title}{id_marker}</b>\n\n"
#             f"🛍️ <b>{product_name[:100]}{'...' if len(product_name) > 100 else ''}</b>\n\n"
#             f"{price_block}"
#         )
#
#         # === Ссылка на товар ===
#         message += f"\n\n🛒 <a href='{url}'>Перейти к товару</a>"
#
#         # === Время проверки ===
#         now = datetime.now().strftime("%d.%m.%Y %H:%M")
#         message += f"\n\n⏰ Проверено: {now}"
#
#         # === Отправляем сообщение ===
#         await bot.send_message(chat_id=telegram_id, text=message, parse_mode='HTML')
#         logger.info(f"✅ Alert sent to user {telegram_id}: {title}")
#         return True
#
#     except Exception as e:
#         logger.error(f"❌ Error sending alert: {type(e).__name__}: {e}")
#         return False
#     finally:
#         await bot.session.close()  # Важно: закрываем сессию!


async def send_price_alert(telegram_id, product_name, old_price, new_price, url, product_id=None, target_price=None):
    """
    Отправляет уведомление об изменении цены через aiogram.

    Формат сообщения — точно по ТЗ пользователя.
    """
    from aiogram import Bot
    from django.conf import settings
    import logging
    from datetime import datetime

    logger = logging.getLogger(__name__)

    token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
    if not token or not telegram_id:
        logger.error("❌ Bot token or telegram_id not found")
        return False

    bot = Bot(token=token)

    try:
        # === 1. Заголовок и эмодзи ===
        if old_price is None:
            emoji = "💰"
            title = "Первая проверка цены!"
        elif new_price < old_price:
            emoji = "📉"
            title = "Цена снизилась!"
        elif new_price > old_price:
            emoji = "📈"
            title = "Цена выросла!"
        else:
            emoji = "➡️"
            title = "Цена не изменилась"

        id_marker = f" [ID:{product_id}]" if product_id else ""

        # === 2. Название товара ===
        name_display = product_name[:100] + ('...' if len(product_name) > 100 else '')
        message = f"{emoji} <b>{title}{id_marker}</b>\n\n"
        message += f"🛍️ <b>{name_display}</b>\n\n"

        # === 3. Блок цен ===
        if old_price is None:
            # Первая проверка
            message += f"💸 Текущая цена: <b>{new_price:,.2f} ₽</b>\n"
        else:
            # Сравнение старой и новой
            message += f"💰 Было: <s>{old_price:,.2f} ₽</s>\n"
            message += f"💸 Стало: <b>{new_price:,.2f} ₽</b>\n"

            # Экономия (только если цена снизилась)
            if new_price < old_price:
                discount = old_price - new_price
                discount_percent = (discount / old_price * 100) if old_price > 0 else 0
                message += f"🎁 Экономия: {discount:,.0f} ₽ ({discount_percent:.0f}%)\n"

        # === 4. Блок целевой цены (НОВОЕ — точно по ТЗ!) ===
        if target_price is not None:
            message += "\n"  # Пустая строка перед блоком цели
            if new_price <= target_price:
                # ✅ Цель достигнута
                message += f"🎯 Ожидаемая цена {target_price:,.2f} ₽ достигнута!\n"
            else:
                # ⏳ Цель ещё не достигнута
                message += f"🎯 Ожидаемая цена {target_price:,.2f} ₽\n"

        # === 5. Ссылка и время ===
        message += f"\n🛒 <a href='{url}'>Перейти к товару</a>"

        now = datetime.now().strftime("%d.%m.%Y %H:%M")
        message += f"\n\n⏰ Проверено: {now}"

        # === 6. Отправка ===
        await bot.send_message(chat_id=telegram_id, text=message, parse_mode='HTML')
        logger.info(f"✅ Alert sent to user {telegram_id}: {title}")
        return True

    except Exception as e:
        logger.error(f"❌ Error sending alert: {type(e).__name__}: {e}")
        return False
    finally:
        await bot.session.close()