#!/usr/bin/env python
"""
Отладочный скрипт с правильным ожиданием динамического контента.
"""
import os, sys, django, logging, time, re
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
django.setup()

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

from tracker.models import Product
from tracker.parsers.wb import _get_chrome_options, _extract_price

product = Product.objects.filter(is_active=True, url__icontains='wildberries').first()
if not product:
    print("❌ Не найдено активных товаров с Wildberries")
    sys.exit(1)

print(f"🔍 Тестируем: ID={product.id}")
print(f"   URL: {product.url[:80]}...")
print(f"   Старая цена: {product.current_price} ₽\n")

driver = None
try:
    print("   [1/5] Инициализация Chrome...")
    options = _get_chrome_options(headless=True)
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    print("   ✅ Chrome запущен")
    
    print("   [2/5] Загрузка страницы...")
    driver.get(product.url)
    
    # === КЛЮЧЕВОЕ: Ждём, пока JS отрендерит контент ===
    print("   [2.5/5] Ожидание рендеринга контента (до 30 сек)...")
    
    # Прокручиваем — это часто триггерит подгрузку
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    
    # Ждём появления ЛЮБОГО элемента с ценой ИЛИ названием
    wait = WebDriverWait(driver, 30)
    try:
        # Пробуем дождаться появления элемента, который точно есть на странице товара
        wait.until(
            EC.presence_of_element_located((
                By.CSS_SELECTOR, 
                '[class*="price"], [data-price], [itemprop="price"], h1.BreadcrumbsProduct__name, [data-testid*="name"]'
            ))
        )
        print("   ✅ Элементы появились! Продолжаем...")
    except:
        print("   ⚠️ Не дождались по CSS — пробуем ждать по наличию текста в body")
        # Фоллбэк: просто ждём 10 секунд
        time.sleep(10)
    
    # Ещё одна прокрутка и пауза
    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(3)
    
    # Проверка на антибот
    print("   [3/5] Проверка на капчу/блокировку...")
    page_source = driver.page_source.lower()
    if 'antibot' in page_source or 'captcha' in page_source or 'проверяем браузер' in page_source:
        print("   ⚠️ Обнаружена антибот-страница!")
        print("   💡 Решение: увеличить задержки, использовать undetected-chromedriver или прокси")
    
    # Поиск цены
    print("   [4/5] Поиск цены...")
    
    # === НОВЫЕ СЕЛЕКТОРЫ: ищем по частичному совпадению класса ===
    price_selectors = [
        # Твой найденный селектор — в гибкой форме:
        (By.CSS_SELECTOR, 'span[class*="priceBlockPrice"]'),
        
        # Паттерны для устойчивости:
        (By.CSS_SELECTOR, '[class*="productPrice"] [class*="price"]'),
        (By.CSS_SELECTOR, '.productSummary [class*="price"]'),
        (By.CSS_SELECTOR, '[class*="PriceCard"] [class*="price"]'),
        
        # Оригинал:
        (By.CSS_SELECTOR, 'span[data-price="current"]'),
        (By.CSS_SELECTOR, 'span.price__current'),
        
        # XPath-варианты:
        (By.XPATH, '//span[contains(@class, "priceBlockPrice")]//h2'),
        (By.XPATH, '//meta[@itemprop="price"]/@content'),
        
        # Фоллбэк:
        (By.CSS_SELECTOR, 'span.price'),
    ]
    
    price = None
    for by, selector in price_selectors:
        try:
            print(f"   🔍 Пробуем: {selector}")
            # Используем find_elements + проверка текста (надёжнее для динамических страниц)
            elements = driver.find_elements(by, selector)
            element = None
            for el in elements:
                text = el.text.strip() if el.tag_name != 'meta' else el.get_attribute('content')
                if text and re.search(r'\d', text):  # есть цифры
                    element = el
                    price_str = text
                    break
            
            if element:
                print(f"      Найдено: '{price_str}'")
                price = _extract_price(price_str)
                if price:
                    print(f"      ✅ Распарсено: {price} ₽")
                    break
                else:
                    print(f"      ❌ Не удалось извлечь число")
            else:
                print(f"      ❌ Элементов с текстом не найдено")
        except Exception as e:
            print(f"      ❌ Ошибка: {type(e).__name__}")
    
    # Поиск названия
    print("   [5/5] Поиск названия...")
    name = None
    name_selectors = [
        (By.CSS_SELECTOR, 'h1.BreadcrumbsProduct__name'),
        (By.CSS_SELECTOR, '[data-testid*="name"]'),
        (By.CSS_SELECTOR, '[class*="BreadcrumbsProduct"] h1'),
        (By.XPATH, '//meta[@property="og:title"]/@content'),
        (By.TAG_NAME, 'h1'),
    ]
    for by, selector in name_selectors:
        try:
            elements = driver.find_elements(by, selector)
            for el in elements:
                name = el.text.strip() if el.tag_name != 'meta' else el.get_attribute('content')
                if name and 3 < len(name) < 250:
                    print(f"   ✅ Название: {name[:60]}...")
                    break
            if name:
                break
        except:
            continue
    
    # Итог
    print(f"\n📦 РЕЗУЛЬТАТ:")
    print(f"   Цена: {price} ₽")
    print(f"   Название: {name}")
    
    if price:
        print(f"\n💾 Сохраняем в БД...")
        old = product.current_price
        product.current_price = price
        if name and not product.name:
            product.name = name
        product.save()
        product.refresh_from_db()
        print(f"   ✅ Обновлено: {old} → {product.current_price} ₽")
    else:
        print(f"\n❌ Цена не найдена.")
        print(f"📄 HTML сохранён: /tmp/wb_debug.html")
        print(f"💡 ОТКРОЙ ЭТОТ ФАЙЛ и найди цену вручную (Ctrl+F → цена товара)")
        
        with open('/tmp/wb_debug.html', 'w', encoding='utf-8') as f:
            f.write(driver.page_source)
        
finally:
    if driver:
        driver.quit()
        print("\n✅ Драйвер закрыт")
