import requests
from curl_cffi import requests as curl_requests
from bs4 import BeautifulSoup
import json
import time


def parse_wildberries(url):
    """
    Парсит цену и название товара со страницы Wildberries.
    """

    # Более полные заголовки, как у реального браузера
    headers = {
        # Добавь в headers:
        'Referer': 'https://www.wildberries.ru/',
        'Origin': 'https://www.wildberries.ru',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0',

    }

    # Используем сессию для сохранения "отпечатка" браузера
    session = requests.Session()

    try:
        # Небольшая случайная задержка (как будто человек думает)
        import time, random
        time.sleep(random.uniform(1, 3))

        # Делаем запрос
        response = session.get(url, headers=headers, timeout=15)
        # response = curl_requests.get(
        #     url,
        #     headers=headers,
        #     timeout=15,
        #     impersonate="chrome120" # Маскируемся под конкретную версию Хром
        # )

        print(f"📡 Статус ответа: {response.status_code}")

        # Проверяем успешность
        if response.status_code != 200:
            print(f"❌ Ошибка загрузки: код {response.status_code}")
            # Попробуем вывести первые 200 символов ответа для отладки
            if response.text:
                print(f"🔍 Начало ответа: {response.text[:200]}...")
            return None, None

        # Парсим HTML
        soup = BeautifulSoup(response.text, 'html.parser')

        # === СПОСОБ 1: Ищем в JSON-LD ===
        price, name = _parse_from_json_ld(soup)
        if price and name:
            print(f"✅ Найдено через JSON-LD: {name} - {price} ₽")
            return price, name

        # === СПОСОБ 2: Ищем по классам ===
        price, name = _parse_from_html_classes(soup)
        if price and name:
            print(f"✅ Найдено через классы: {name} - {price} ₽")
            return price, name

        print("❌ Не удалось найти цену ни одним из способов")
        return None, None

    except requests.exceptions.Timeout:
        print("❌ Таймаут: сайт не ответил за 15 секунд")
        return None, None
    except requests.exceptions.ConnectionError:
        print("❌ Ошибка соединения: проверь интернет или доступность сайта")
        return None, None
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {type(e).__name__}: {e}")
        return None, None
    finally:
        session.close()  # Закрываем сессию

def _parse_from_json_ld(soup):
    """
    Ищет данные в JSON-LD скрипте (самый надежный способ).
    Wildberries часто хранит данные о товаре в скрытом JSON.
    """
    try:
        # ищем все скрипты с JSON-LD
        scripts = soup.find_all('script', type='application/ld+json')

        for script in scripts:
            if script.string:
                try:
                    data = json.loads(script.string)

                    # Проверяем, есть ли там данные о товаре
                    if isinstance(data, dict):
                        # Иногда данные вложенные
                        if 'offers' in data:
                            offers = data['offers']
                            if isinstance(offers, dict) and 'price' in offers:
                                price = float(offers['price'])
                                name = data.get('name', 'Без названия')
                                return price, name

                        # Или данные в массиве
                        if isinstance(data, list):
                            for item in data:
                                if 'offers' in item:
                                    offers = item['offers']
                                    if isinstance(offers, dict) and 'price' in offers:
                                        price = float(offers['price'])
                                        name = item.get('name', 'Без названия')
                                        return price, name
                except json.JSONDecodeError:
                    continue

    except Exception as e:
        print(f"Ошибка парсинга JSON-LD: {e}")

    return None, None

def _parse_from_html_classes(soup):
    """
    Ищет цену по HTML-классам (менее надежно, классы могут меняться)
    """
    try:
        # Пробуем найти цену по разным возможным классам
        price_selectors = [
            {'class': 'price__current-price'},
            {'class': 'price-block__price'},
            {'data-price': True},
            {'class': 'price'},
        ]

        for selector in price_selectors:
            price_tag = soup.find('span', selector)
            if price_tag:
                # очищаем цену от пробелов и символа ₽
                price_text = price_tag.get_text(strip=True).replace('₽', '').replace(' ', '')
                try:
                    price = float(price_text)
                    # пытаемся найти название
                    name_tag = soup.find('h1', {'class': 'product-page-name'})
                    name = name_tag.get_text(strip=True) if name_tag else 'Без названия'
                    return price, name
                except ValueError:
                    continue

    except Exception as e:
        print(f"Ошибка парсинга HTML-классов: {e}")

    return None, None





# === ЗАГЛУШКА ДЛЯ РАЗРАБОТКИ (раскомментируй, если реальный парсинг не работает) ===

# def parse_wildberries_mock(url):
#     """
#     Возвращает тестовые данные вместо реального парсинга.
#     Используется для разработки, когда сайт блокирует запросы.
#     """
#     import random
#
#     # Имитируем "задержку сети"
#     time.sleep(0.5)
#
#     # Генерируем случайную цену рядом с целевой
#     # В реальном проекте здесь будет логика получения актуальной цены
#     mock_prices = {
#         '757984979': (4990.00, 'Кроссовки мужские спортивные'),
#         '12345678': (1299.00, 'Футболка хлопковая'),
#     }
#
#     # Извлекаем ID товара из ссылки
#     import re
#     match = re.search(r'/catalog/(\d+)/', url)
#     if match:
#         product_id = match.group(1)
#         if product_id in mock_prices:
#             price, name = mock_prices[product_id]
#             # Добавляем немного случайности к цене
#             price = price + random.uniform(-100, 100)
#             print(f"🎭 [MOCK] {name} - {price:.2f} ₽")
#             return round(price, 2), name
#
#     # Дефолтные тестовые данные
#     print("🎭 [MOCK] Возвращаем тестовые данные")
#     return 2999.00, 'Тестовый товар'
#
# # === Переключаем функцию для тестов ===
# # Раскомментируй строку ниже, если реальный парсинг не работает:
# parse_wildberries = parse_wildberries_mock


def parse_wildberries_mock(url):
    """
    Возвращает тестовые данные вместо реального парсинга.
    Генерирует случайную цену, чтобы видеть изменения в админке.
    """
    import random
    import re
    import time

    # Имитируем задержку сети
    time.sleep(0.5)

    # Извлекаем ID товара из ссылки (для разнообразия)
    match = re.search(r'/catalog/(\d+)/', url)
    base_price = 3000
    if match:
        # Используем ID товара как "зерно" для случайности
        product_id = int(match.group(1))
        base_price = (product_id % 5000) + 1000

    # Добавляем случайное отклонение от -500 до +500 рублей
    random_offset = random.uniform(-500, 500)
    price = round(base_price + random_offset, 2)

    # Генерируем название
    name = 'Тестовый товар WB'
    if match:
        name = f'Товар #{match.group(1)}'

    print(f"🎭 [MOCK] {name} - {price} ₽ (база: {base_price}, отклонение: {random_offset:.2f})")
    return price, name

parse_wildberries = parse_wildberries_mock





# === Тестовый запуск ===
if __name__ == '__main__':
    # Тестовая ссылка (заменить)
    test_url = 'https://www.wildberries.ru/catalog/327491645/detail.aspx?targetUrl=MI'
    print(f"Тестируем парсер на: {test_url}")
    price, name = parse_wildberries(test_url)
    if price:
        print(f"Успех: {name} - {price}  ₽")
    else:
        print("Не удалось спарсить цену")




