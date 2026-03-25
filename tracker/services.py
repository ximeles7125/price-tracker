from .models import Product
from .parsers.wb import parse_wildberries


def update_product_price(product_id):
    """
    Обновляет цену для товара с указанным ID.

    Args:
        product_id (int): ID товара в базе данных

    Returns:
        bool: True если успешно, False если ошибка
    """
    try:
        # Получаем товар из базы
        product = Product.objects.get(id=product_id)

        # Определяем, какой парсер использовать
        if 'wildberries' in product.url.lower():
            new_price, new_name = parse_wildberries(product.url)
        else:
            print(f"❌ Неизвестный маркетплейс: {product.url}")
            return False

        # Если цена найдена — обновляем
        if new_price is not None:
            old_price = product.current_price

            # Обновляем поля
            product.current_price = new_price
            if new_name and not product.name:
                product.name = new_name
            product.save()

            print(f"✅ Цена обновлена: {product.name}")
            print(f"   Было: {old_price} ₽ → Стало: {new_price} ₽")

            # Проверяем, не достигли ли желаемой цены
            if product.current_price <= product.target_price:
                print(f"🔥 ВНИМАНИЕ: Цена достигла желаемой ({product.target_price} ₽)!")
                # Здесь позже добавим отправку уведомления в Telegram

            return True
        else:
            print(f"❌ Не удалось получить цену для товара {product.id}")
            return False

    except Product.DoesNotExist:
        print(f"❌ Товар с ID {product_id} не найден")
        return False
    except Exception as e:
        print(f"❌ Ошибка при обновлении цены: {e}")
        return False


def update_all_active_products():
    """
    Обновляет цены для всех активных товаров.
    """
    products = Product.objects.filter(is_active=True)
    print(f"🔄 Начинаем проверку {products.count()} товаров...")

    success_count = 0
    fail_count = 0

    for product in products:
        if update_product_price(product.id):
            success_count += 1
        else:
            fail_count += 1

        # Небольшая задержка между запросами (чтобы не блокировали)
        import time
        time.sleep(1)

    print(f"✅ Готово! Успешно: {success_count}, Ошибок: {fail_count}")