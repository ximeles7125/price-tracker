"""
Парсер Wildberries через Selenium с улучшенной эмуляцией браузера.
"""

import logging
import re
import time
import random
import shutil
import os
from typing import Optional, Tuple
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

logger = logging.getLogger(__name__)

# === Реалистичные User-Agent (ротация) ===
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
]


def _get_random_user_agent() -> str:
    return random.choice(USER_AGENTS)


def _extract_price(text: str) -> Optional[float]:
    """
    Извлекает цену из строки, поддерживает форматы WB.

    Поддерживает:
    • "1 299 ₽" → 1299.0
    • "1 299,99 ₽" → 1299.99
    • "1,299.50" → 1299.5
    • "1299" → 1299.0
    • "7 097 ₽\n7 242 ₽" → 7097.0 (берёт первую)
    • "1\xa0000 ₽" → 1000.0 (неразрывный пробел)
    """
    if not text:
        return None
    try:
        text = str(text).strip()

        # Обработка множественных цен (берём первую)
        if '\n' in text:
            text = text.split('\n')[0].strip()

        # Нормализуем пробелы (включая неразрывные)
        text = re.sub(r'[\s\u00a0\u202f\u2009]+', ' ', text)

        # Удаляем всё кроме цифр, точки и запятой
        cleaned = re.sub(r'[^\d.,]', '', text.replace(',', '.'))

        if cleaned:
            price = float(cleaned)
            # Проверка на разумный диапазон
            if 0 < price < 10_000_000:
                return price
    except (ValueError, TypeError):
        pass
    return None


def _human_delay(min_sec: float = 2.0, max_sec: float = 5.0):
    """Человекоподобная задержка с небольшим джиттером."""
    base = random.uniform(min_sec, max_sec)
    jitter = random.uniform(-0.3, 0.3)
    time.sleep(max(0.5, base + jitter))


def _get_chrome_options(headless: bool = True) -> Options:
    """
    Настройки Chrome с явным путём к браузеру (для snap/системных установок).
    """
    options = Options()
    if headless:
        options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option('excludeSwitches', ['enable-automation'])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument(f'user-agent={_get_random_user_agent()}')

    # === Явный путь к браузеру (для snap Chromium) ===
    chrome_paths = [
        '/snap/chromium/current/usr/lib/chromium-browser/chrome',  # snap (Linux)
        '/usr/bin/chromium',
        '/usr/bin/chromium-browser',
        '/usr/bin/google-chrome',
        '/usr/bin/google-chrome-stable',
        '/opt/google/chrome/chrome',
    ]

    for path in chrome_paths:
        if os.path.exists(path):
            options.binary_location = path
            logger.info(f"🔧 Используем Chrome: {path}")
            break
    else:
        # Фоллбэк: ищем через which
        chrome_bin = shutil.which('chromium') or shutil.which('chromium-browser') or shutil.which('google-chrome')
        if chrome_bin:
            options.binary_location = chrome_bin
            logger.info(f"🔧 Используем Chrome (через which): {chrome_bin}")

    return options


def _get_price_via_selenium(
        url: str,
        timeout: int = 40,
        headless: bool = True
) -> Tuple[Optional[float], Optional[str]]:
    """
    Упрощённый Selenium только для цены и названия (фоллбэк).

    Returns:
        tuple: (price: float|None, name: str|None)
    """
    logger.info(f"🕷️ Selenium (fallback): парсинг {url}")

    driver = None
    price, name = None, None

    try:
        # === 1. Человекоподобная задержка перед запуском ===
        _human_delay(2.0, 4.0)

        # === 2. Настройки Chrome ===
        options = _get_chrome_options(headless=headless)

        # === 3. Явный путь к chromedriver ===
        driver_path = shutil.which('chromedriver') or '/usr/bin/chromedriver'
        service = Service(executable_path=driver_path)

        driver = webdriver.Chrome(service=service, options=options)

        # === 4. Скрытие признаков автоматизации ===
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        driver.execute_script("Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3]})")
        driver.execute_script(
            "Object.defineProperty(navigator, 'languages', {get: () => ['ru-RU', 'ru', 'en-US', 'en']})")

        # === 5. Загрузка страницы ===
        _human_delay(1.0, 2.5)
        driver.get(url)

        # === 6. Ожидание рендеринга контента ===
        _human_delay(3.0, 6.0)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 3);")
        _human_delay(2.0, 4.0)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 2);")
        _human_delay(2.0, 4.0)
        driver.execute_script("window.scrollTo(0, 0);")
        _human_delay(2.0, 4.0)

        wait = WebDriverWait(driver, timeout)

        # === 7. Извлечение цены ===
        price_selectors = [
            (By.XPATH, '//span[contains(@class, "priceBlockPrice")]//h2'),
            (By.XPATH, '//span[contains(@class, "priceBlockPrice")]'),
            (By.CSS_SELECTOR, 'span[class*="priceBlockPrice"]'),
            (By.CSS_SELECTOR, '[class*="productPrice"] [class*="price"]'),
            (By.CSS_SELECTOR, '.productSummary [class*="price"]'),
            (By.CSS_SELECTOR, 'span[data-price="current"]'),
            (By.XPATH, '//meta[@itemprop="price"]'),
        ]

        for by, selector in price_selectors:
            try:
                elements = wait.until(
                    EC.presence_of_all_elements_located((by, selector)),
                    message=f"Timeout для {selector}"
                )

                for el in elements:
                    if el.tag_name == 'meta':
                        text = el.get_attribute('content') or ''
                    else:
                        text = el.text.strip()

                    if text and re.search(r'\d', text):
                        if '\n' in text:
                            text = text.split('\n')[0].strip()
                        price = _extract_price(text)
                        if price:
                            logger.info(f"✅ Цена найдена: {price} ₽ (селектор: {selector})")
                            break
                if price:
                    break
            except Exception as e:
                logger.debug(f"⚠️ Селектор цены {selector} не сработал: {type(e).__name__}")
                continue

        # === 8. Извлечение названия (с фильтрацией сайта) ===
        if not name:
            name_selectors = [
                # ✅ НОВЫЕ: Конкретные селекторы Wildberries для названия товара
                (By.CSS_SELECTOR, 'h2[class*="productTitle"]'),  # ← КЛЮЧЕВОЙ!
                (By.CSS_SELECTOR, 'h1.BreadcrumbsProduct__name'),
                (By.CSS_SELECTOR, 'h1.product-page__title'),
                (By.CSS_SELECTOR, '[data-testid="product-name"]'),
                (By.CSS_SELECTOR, '.productPageHeader h1'),
                (By.CSS_SELECTOR, '.productHeader h1'),
                # ✅ Meta-теги — но с фильтрацией
                (By.XPATH, '//meta[@property="og:title"]'),
                (By.XPATH, '//meta[@name="title"]'),
            ]

            for by, selector in name_selectors:
                try:
                    element = wait.until(
                        EC.presence_of_element_located((by, selector)),
                        message=f"Timeout для {selector}"
                    )

                    if element.tag_name == 'meta':
                        raw_name = element.get_attribute('content') or ''
                    else:
                        raw_name = element.text.strip()

                    # ✅ ФИЛЬТРАЦИЯ: убираем название сайта
                    cleaned_name = _clean_product_name(raw_name)

                    if cleaned_name and 3 < len(cleaned_name) < 250:
                        name = cleaned_name
                        logger.info(f"✅ Название найдено: {name[:50]}... (селектор: {selector})")
                        break
                except Exception as e:
                    logger.debug(f"⚠️ Селектор названия {selector} не сработал: {type(e).__name__}")
                    continue

        # === 9. Фоллбэк: извлечение через JavaScript ===
        if price is None or not name:
            logger.debug("🔍 Фоллбэк: извлечение через JavaScript...")
            try:
                js_result = driver.execute_script("""
                    const result = { price: null, name: null };

                    // Поиск цены
                    const priceEls = document.querySelectorAll(
                        'span[class*="priceBlockPrice"], [class*="productPrice"] [class*="price"], [data-price]'
                    );
                    for (let el of priceEls) {
                        const text = el.textContent || el.getAttribute('content');
                        if (text && /\\d+[\\s.,]*\\d+/.test(text)) {
                            result.price = text.trim().split('\\n')[0];
                            break;
                        }
                    }

                    // Поиск названия — только конкретные селекторы
                    const nameEls = document.querySelectorAll(
                        'h1.BreadcrumbsProduct__name, h1.product-page__title, [data-testid="product-name"], .productPageHeader h1'
                    );
                    for (let el of nameEls) {
                        const text = el.textContent;
                        if (text && text.length > 3 && text.length < 250 && !/wildberries/i.test(text) && !/интернет-магазин/i.test(text)) {
                            result.name = text.trim();
                            break;
                        }
                    }

                    return result;
                """)

                if price is None and js_result.get('price'):
                    price = _extract_price(js_result['price'])
                    if price:
                        logger.info(f"✅ Цена найдена через JS: {price} ₽")

                if not name and js_result.get('name'):
                    cleaned = _clean_product_name(js_result['name'])
                    if cleaned and 3 < len(cleaned) < 250:
                        name = cleaned
                        logger.info(f"✅ Название найдено через JS: {name[:50]}...")

            except Exception as e:
                logger.debug(f"⚠️ JS-фоллбэк не сработал: {type(e).__name__}")

        logger.info(f"✅ Selenium fallback: цена={price}, название={name[:50] if name else None}...")
        return price, name

    except Exception as e:
        logger.error(f"❌ Selenium ошибка: {type(e).__name__}: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return None, None

    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass


def _clean_product_name(raw_name: str) -> Optional[str]:
    """
    Очищает название товара от мусора: названия сайта, лишних символов.

    Примеры:
    • "Интернет-магазин : широкий ассортимент товаров" → None
    • "Wildberries - Шины летние 215 65 R16" → "Шины летние 215 65 R16"
    • "Шины летние 215/65 R16 Cf1100 XL 102H" → "Шины летние 215/65 R16 Cf1100 XL 102H"
    """
    if not raw_name:
        return None

    name = raw_name.strip()

    # === Список фраз, которые указывают на название сайта (НЕ товара) ===
    site_only_phrases = [
        'интернет-магазин', 'интернет магазин',
        'широкий ассортимент', 'ассортимент товаров',
        'товаров в интернет-магазине', 'в интернет-магазине',
        'бесплатная доставка', 'постоянные скидки',
        'купить в интернет-магазине', 'заказать с доставкой',
    ]

    # === Если строка содержит ТОЛЬКО маркеры сайта — отбрасываем ===
    name_lower = name.lower()
    if any(phrase in name_lower for phrase in site_only_phrases):
        # Проверяем, есть ли в строке что-то кроме маркеров сайта
        cleaned = name
        for phrase in site_only_phrases:
            cleaned = re.sub(re.escape(phrase), '', cleaned, flags=re.I)
        cleaned = re.sub(r'\s+[\|\-\:•]+\s+', ' ', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()

        # Если после очистки осталось что-то осмысленное — возвращаем
        if 3 < len(cleaned) < 250 and re.search(r'[\wа-яё/]', cleaned, re.I):
            return cleaned
        # Иначе — отбрасываем
        return None

    # === Разделители, по которым режем название ===
    separators = [' : ', ' | ', ' - ', ' — ', ' • ', ' :: ', ' // ']

    # === Разбиваем по разделителям и проверяем каждую часть ===
    parts = [name]
    for sep in separators:
        if sep in name:
            parts = name.split(sep)
            break

    # === Ищем часть, которая НЕ содержит маркеров сайта ===
    site_markers = [
        'wildberries', 'wb.ru', 'wildberries.ru',
        'интернет-магазин', 'интернет магазин',
        'купить', 'доставка', 'цена', 'отзывы',
        'распродажа', 'скидки', 'акции', 'онлайн',
    ]

    for part in parts:
        part = part.strip()
        part_lower = part.lower()

        # Если часть не содержит маркеров сайта и достаточно длинная — это название товара
        if not any(marker in part_lower for marker in site_markers):
            if 3 < len(part) < 250 and re.search(r'[\wа-яё/]', part, re.I):
                return re.sub(r'\s+', ' ', part).strip()

    # === Фоллбэк: берём первую часть, но очищаем от маркеров ===
    first_part = parts[0].strip()
    for marker in site_markers + site_only_phrases:
        first_part = re.sub(re.escape(marker), '', first_part, flags=re.I)
    first_part = re.sub(r'\s+[\|\-\:•]+\s+', ' ', first_part)
    first_part = re.sub(r'\s+', ' ', first_part).strip()

    if 3 < len(first_part) < 250 and re.search(r'[\wа-яё/]', first_part, re.I):
        return first_part

    return None


def parse_wildberries(
        url: str,
        timeout: int = 40,
        headless: bool = True,
        use_api_first: bool = False  # Отключено, пока внутренний API не работает стабильно
) -> Tuple[Optional[float], Optional[str]]:
    """
    Основной метод парсинга Wildberries.

    Приоритет:
    1. Внутренний API (если use_api_first=True и работает)
    2. Selenium (фоллбэк, основной метод)
    """
    logger.info(f"🔍 parse_wildberries вызван: {url}")

    price, name = None, None

    # === Попытка 1: Внутренний API (опционально) ===
    if use_api_first:
        try:
            from .wb_internal_api import parse_wildberries_internal_api
            price, name = parse_wildberries_internal_api(url)

            if price is not None or name:
                logger.info(f"✅ Internal API вернул данные: цена={price} ₽, название={name[:50] if name else None}...")
                return price, name
            else:
                logger.warning("⚠️ Internal API не вернул данных, пробуем Selenium...")
        except ImportError as e:
            logger.warning(f"⚠️ Модуль wb_internal_api не найден: {e}")
        except Exception as e:
            logger.warning(f"⚠️ Internal API ошибка: {type(e).__name__}: {e}")

    # === Попытка 2: Selenium (основной метод) ===
    logger.info("🕷️ Selenium: парсинг цены и названия")
    return _get_price_via_selenium(url, timeout=timeout, headless=headless)


def parse_wildberries_sync(url: str, **kwargs) -> Tuple[Optional[float], Optional[str]]:
    """Синхронная обёртка для Celery."""
    return parse_wildberries(url, **kwargs)