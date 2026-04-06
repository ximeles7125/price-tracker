"""
Парсер Wildberries через Selenium с анти-детект настройками.
Без undetected_chromedriver (совместимо с Python 3.13)
"""

import logging
import time
import random
import re
from typing import Optional, Tuple
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

logger = logging.getLogger(__name__)

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
]


def _get_random_user_agent() -> str:
    return random.choice(USER_AGENTS)


def _get_chrome_options(headless: bool = True) -> Options:
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
    options.add_argument(f'--user-agent={_get_random_user_agent()}')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-popup-blocking')
    options.add_argument('--disable-notifications')
    return options


def _extract_price(text: str) -> Optional[float]:
    if not text:
        return None
    try:
        text = str(text).strip()
        text = re.sub(r'[\s\u00a0\u202f\u2009]+', ' ', text)
        cleaned = re.sub(r'[^\d.,]', '', text.replace(',', '.'))
        if cleaned:
            price = float(cleaned)
            if 0 < price < 10_000_000:
                return price
    except (ValueError, TypeError):
        pass
    return None


def _is_antibot_page(driver) -> bool:
    """Проверяет, показана ли антибот-страница."""
    try:
        source = driver.page_source.lower()
        antibot_signals = ['antibot', 'challenge', 'проверяем браузер', 'captcha', 'access denied']
        return any(signal in source for signal in antibot_signals)
    except:
        return False


def parse_wildberries(
        url: str,
        timeout: int = 30,
        headless: bool = True,
        delay_range: Tuple[float, float] = (3.0, 7.0)
) -> Tuple[Optional[float], Optional[str]]:
    logger.info(f"🕷️ Selenium: парсинг {url}")

    driver = None
    try:
        # Случайная задержка перед запуском
        time.sleep(random.uniform(*delay_range))

        # Инициализация драйвера
        options = _get_chrome_options(headless=headless)
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)

        # Скрываем признаки WebDriver
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        driver.execute_script("Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3]})")
        driver.execute_script("Object.defineProperty(navigator, 'languages', {get: () => ['ru-RU', 'ru']})")

        # Загрузка страницы
        driver.get(url)

        # Ждём загрузки (антибот может грузиться 10-20 сек)
        logger.debug("   Ожидание загрузки страницы...")
        time.sleep(random.uniform(8.0, 15.0))

        # Прокрутка для имитации человека
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(2)

        # Проверка на антибот
        if _is_antibot_page(driver):
            logger.warning("⚠️ Обнаружена антибот-страница! Ждём...")
            time.sleep(15)
            if _is_antibot_page(driver):
                logger.warning("⚠️ Антибот остался, обновляем страницу...")
                driver.refresh()
                time.sleep(random.uniform(8.0, 15.0))

        if _is_antibot_page(driver):
            logger.error("❌ Не удалось пройти антибот-проверку")
            # Сохраняем HTML для анализа
            with open('/tmp/wb_antibot.html', 'w', encoding='utf-8') as f:
                f.write(driver.page_source)
            logger.warning(f"📄 HTML сохранён: /tmp/wb_antibot.html")
            return None, None

        wait = WebDriverWait(driver, timeout)

        # === Название ===
        name = None
        name_selectors = [
            (By.CSS_SELECTOR, 'h1.BreadcrumbsProduct__name'),
            (By.CSS_SELECTOR, 'h1.product-page__title'),
            (By.CSS_SELECTOR, '[data-testid*="name"]'),
            (By.XPATH, '//meta[@property="og:title"]/@content'),
            (By.TAG_NAME, 'h1'),
        ]

        for by, selector in name_selectors:
            try:
                if '/@content' in selector:
                    element = wait.until(EC.presence_of_element_located((By.XPATH, selector.replace('/@content', ''))))
                    name = element.get_attribute('content')
                else:
                    element = wait.until(EC.presence_of_element_located((by, selector)))
                    name = element.text.strip()
                if name and 3 < len(name) < 250:
                    name = re.sub(r'\s+', ' ', name).strip()
                    logger.debug(f"✅ Название найдено: {name[:50]}...")
                    break
            except Exception:
                continue

        # === Цена ===
        price = None
        price_selectors = [
            (By.CSS_SELECTOR, 'span[class*="priceBlockPrice"]'),
            (By.CSS_SELECTOR, '[class*="productPrice"] [class*="price"]'),
            (By.CSS_SELECTOR, '.productSummary [class*="price"]'),
            (By.CSS_SELECTOR, 'span[data-price="current"]'),
            (By.CSS_SELECTOR, 'span.price__current'),
            (By.XPATH, '//meta[@itemprop="price"]/@content'),
        ]

        for by, selector in price_selectors:
            try:
                if '/@content' in selector:
                    element = wait.until(EC.presence_of_element_located((By.XPATH, selector.replace('/@content', ''))))
                    price_str = element.get_attribute('content')
                else:
                    elements = driver.find_elements(by, selector)
                    element = None
                    for el in elements:
                        if el.text.strip():
                            element = el
                            break
                    if not element:
                        continue
                    price_str = element.text.strip()

                logger.debug(f"🔍 Найдено через '{selector}': '{price_str}'")
                price = _extract_price(price_str)
                if price:
                    logger.info(f"✅ Цена найдена: {price} ₽")
                    break
            except Exception as e:
                logger.debug(f"❌ Селектор '{selector}' не сработал: {type(e).__name__}")
                continue

        # === JS-фоллбэк ===
        if price is None:
            logger.debug("🔍 Фоллбэк: извлечение цены через JavaScript...")
            try:
                price_js = driver.execute_script("""
                    const candidates = document.querySelectorAll(
                        'span[class*="priceBlockPrice"], [class*="productPrice"] span, [data-price]'
                    );
                    for (let el of candidates) {
                        const text = el.textContent || el.getAttribute('content');
                        if (text && /\\d+[\\s.,]*\\d+/.test(text)) {
                            return text.trim();
                        }
                    }
                    return null;
                """)
                if price_js:
                    logger.debug(f"   Найдено через JS: '{price_js}'")
                    price = _extract_price(price_js)
                    if price:
                        logger.info(f"✅ Цена найдена через JS: {price} ₽")
            except Exception as e:
                logger.debug(f"❌ JS-извлечение: {type(e).__name__}")

        logger.info(f"✅ Selenium: цена={price}, название={name[:50] if name else None}...")
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


def parse_wildberries_sync(url: str, **kwargs) -> Tuple[Optional[float], Optional[str]]:
    """Синхронная обёртка для Celery."""
    return parse_wildberries(url, **kwargs)