"""
Парсер метаданных товара через прямой API Wildberries.
Возвращает название и бренд, но НЕ цену.
"""

import logging
import re
import random
from typing import Optional, Tuple
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

BASKET_SERVERS = [
    'basket-01.wbbasket.ru', 'basket-02.wbbasket.ru', 'basket-11.wbbasket.ru',
    'basket-15.wbbasket.ru', 'basket-17.wbbasket.ru', 'basket-19.wbbasket.ru',
]


def extract_nm_id(url: str) -> Optional[str]:
    """Извлекает nm_id из ссылки товара."""
    match = re.search(r'/catalog/(\d+)/', url)
    return match.group(1) if match else None


def parse_wildberries_metadata_api(
        url: str,
        timeout: float = 10.0
) -> Tuple[Optional[str], Optional[str]]:
    """
    Парсит название и бренд через прямой API Wildberries.

    Returns:
        tuple: (name: str|None, brand: str|None)
    """
    logger.info(f"🌐 API (metadata): парсинг {url}")

    nm_id = extract_nm_id(url)
    if not nm_id:
        logger.error(f"❌ Не удалось извлечь nm_id из {url}")
        return None, None

    vol = f"vol{nm_id[:4]}"
    part = f"part{nm_id[:6]}"
    server = random.choice(BASKET_SERVERS)

    api_url = f"https://{server}/{vol}/{part}/{nm_id}/info/ru/card.json"

    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
        'Accept': 'application/json',
        'Referer': 'https://www.wildberries.ru/',
    }

    session = requests.Session()
    retry = Retry(total=2, backoff_factor=0.3, status_forcelist=[429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('https://', adapter)

    try:
        response = session.get(api_url, headers=headers, timeout=timeout)
        response.raise_for_status()
        data = response.json()

        # Извлекаем название
        name = data.get('imt_name') or data.get('name') or data.get('title')
        if name and isinstance(name, str) and 3 < len(name) < 250:
            name = re.sub(r'\s+', ' ', name).strip()

        # Извлекаем бренд
        selling = data.get('selling', {})
        brand = selling.get('brand_name') if isinstance(selling, dict) else None

        logger.info(f"✅ API metadata: name={name[:50] if name else None}..., brand={brand}")
        return name, brand

    except requests.RequestException as e:
        logger.warning(f"⚠️ Ошибка API metadata: {e}")
        return None, None