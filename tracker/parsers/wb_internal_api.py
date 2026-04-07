"""
Парсер Wildberries через внутренние API.
Использует два эндпоинта:
1. basket-*.wbbasket.ru/.../card.json — метаданные (название, бренд)
2. /__internal/u-card/cards/v4/detail — цена и доп. данные

Важно: цена в ответе указана в копейках (последние 2 цифры), нужно делить на 100.
"""

import logging
import re
import random
from typing import Optional, Tuple, Dict, Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

# Пул серверов basket для метаданных
BASKET_SERVERS = [
    'basket-01.wbbasket.ru', 'basket-02.wbbasket.ru', 'basket-11.wbbasket.ru',
    'basket-15.wbbasket.ru', 'basket-17.wbbasket.ru', 'basket-19.wbbasket.ru',
]

# Фиксированный dest (координаты Москвы) — можно менять для гео-тестов
DEFAULT_DEST = "-1259570983"


def extract_nm_id(url: str) -> Optional[str]:
    """
    Извлекает nm_id (ID товара) из ссылки Wildberries.
    Пример: /catalog/162246509/detail.aspx → "162246509"
    """
    match = re.search(r'/catalog/(\d+)/', url)
    return match.group(1) if match else None


def _create_session() -> requests.Session:
    """Создаёт сессию с retry-логикой."""
    session = requests.Session()
    retry = Retry(
        total=2,
        backoff_factor=0.3,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=['GET']
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('https://', adapter)
    return session


def _get_metadata(nm_id: str, timeout: float = 10.0) -> Optional[Dict[str, Any]]:
    """
    Получает метаданные товара (название, бренд, характеристики) из basket-API.
    """
    vol = f"vol{nm_id[:4]}"
    part = f"part{nm_id[:7]}"
    server = random.choice(BASKET_SERVERS)

    url = f"https://{server}/{vol}/{part}/{nm_id}/info/ru/card.json"

    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
        'Accept': 'application/json',
        'Referer': 'https://www.wildberries.ru/',
    }

    try:
        session = _create_session()
        response = session.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.debug(f"⚠️ Ошибка получения метаданных для nm_id={nm_id}: {e}")
        return None


def _get_price_data(
        nm_id: str,
        dest: str = DEFAULT_DEST,
        curr: str = 'rub',
        timeout: float = 10.0
) -> Optional[Dict[str, Any]]:
    """
    Получает данные о цене через внутренний API Wildberries.

    Важно: цена в ответе указана в копейках (последние 2 цифры).
    Пример: "product": 539000 → 5390.00 ₽
    """
    # Формируем список nm_id (можно передавать несколько через ;)
    nm_list = nm_id

    url = (
        "https://www.wildberries.ru/__internal/u-card/cards/v4/detail"
        f"?curr={curr}&dest={dest}&nm={nm_list}&appType=1&lang=ru"
    )

    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json',
        'Referer': 'https://www.wildberries.ru/',
        'Origin': 'https://www.wildberries.ru',
        'sec-ch-ua': '"Chromium";v="120", "Not(A:Brand";v="24", "Google Chrome";v="120"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Linux"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
    }

    try:
        session = _create_session()
        response = session.get(url, headers=headers, timeout=timeout)

        # Wildberries может вернуть 498/403 при подозрении на бота
        if response.status_code in [403, 498]:
            logger.warning(f"⚠️ Доступ запрещён (статус {response.status_code}) для nm_id={nm_id}")
            return None

        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.debug(f"⚠️ Ошибка получения цены для nm_id={nm_id}: {e}")
        return None


def _convert_kopecks_to_rub(value: Any) -> Optional[float]:
    """
    Конвертирует значение из копейек в рубли.
    Пример: 539000 → 5390.0
    """
    if value is None:
        return None
    try:
        # Если число — делим на 100
        if isinstance(value, (int, float)):
            rubles = value / 100.0
            # Проверка на разумный диапазон
            if 0 < rubles < 10_000_000:
                return round(rubles, 2)
        # Если строка — пробуем распарсить
        if isinstance(value, str):
            cleaned = re.sub(r'[^\d.]', '', value)
            if cleaned:
                return _convert_kopecks_to_rub(float(cleaned))
    except (ValueError, TypeError):
        pass
    return None


def _extract_name_from_metadata(metadata: Dict[str, Any]) -> Optional[str]:
    """Извлекает название товара из метаданных."""
    # Пробуем разные поля
    for key in ['imt_name', 'name', 'title', 'productName']:
        if key in metadata and isinstance(metadata[key], str):
            name = metadata[key].strip()
            if 3 < len(name) < 250:
                return re.sub(r'\s+', ' ', name)
    return None


def _extract_brand_from_metadata(metadata: Dict[str, Any]) -> Optional[str]:
    """Извлекает бренд из метаданных."""
    selling = metadata.get('selling', {})
    if isinstance(selling, dict):
        brand = selling.get('brand_name')
        if isinstance(brand, str) and brand:
            return brand.strip()
    return None


def parse_wildberries_internal_api(
        url: str,
        timeout: float = 10.0
) -> Tuple[Optional[float], Optional[str]]:
    """
    Основной метод парсинга через внутренние API Wildberries.

    Args:
        url: Ссылка на страницу товара
        timeout: Таймаут запросов в секундах

    Returns:
        tuple: (price: float|None, name: str|None)
    """
    logger.info(f"🌐 Internal API: парсинг {url}")

    # Извлекаем nm_id
    nm_id = extract_nm_id(url)
    if not nm_id:
        logger.error(f"❌ Не удалось извлечь nm_id из {url}")
        return None, None

    # === Шаг 1: Получаем цену (приоритет) ===
    price_data = _get_price_data(nm_id, timeout=timeout)
    price = None

    if price_data and isinstance(price_data, dict):
        # Ищем поле "product" — это корректная цена в копейках
        product_price = price_data.get('product')
        if product_price is not None:
            price = _convert_kopecks_to_rub(product_price)
            logger.debug(f"   Цена из 'product': {product_price} коп → {price} ₽")

        # Если "product" нет, пробуем "price" (резервный вариант)
        if price is None:
            fallback_price = price_data.get('price')
            if fallback_price is not None:
                price = _convert_kopecks_to_rub(fallback_price)
                logger.debug(f"   Цена из 'price': {fallback_price} коп → {price} ₽")

        # Название тоже может быть в price_data
        name = price_data.get('name') or price_data.get('title')
        if name and isinstance(name, str) and 3 < len(name) < 250:
            name = re.sub(r'\s+', ' ', name).strip()
            logger.info(f"✅ Internal API: цена={price} ₽, название={name[:50]}...")
            return price, name

    # === Шаг 2: Если название не найдено — берём из метаданных ===
    if price is None or 'name' not in (price_data or {}):
        metadata = _get_metadata(nm_id, timeout=timeout)
        if metadata and isinstance(metadata, dict):
            if price is None:
                # Цена в метаданных обычно не указана, но на всякий случай проверим
                meta_price = metadata.get('price')
                if meta_price:
                    price = _convert_kopecks_to_rub(meta_price)

            name = _extract_name_from_metadata(metadata)
            brand = _extract_brand_from_metadata(metadata)

            full_name = f"{brand} {name}" if brand and name else (name or brand)

            logger.info(f"✅ Internal API: цена={price} ₽, название={full_name[:50] if full_name else None}...")
            return price, full_name

    logger.warning(f"⚠️ Не удалось получить данные для nm_id={nm_id}")
    return None, None