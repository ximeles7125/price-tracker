#!/usr/bin/env python
"""Минимальный тест: открывает страницу и закрывает браузер"""
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

print("🚀 Запускаем минимальный тест Chrome...")

options = Options()
options.add_argument('--headless=new')
options.add_argument('--no-sandbox')
options.add_argument('--disable-gpu')

try:
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    print("✅ Chrome запустился!")
    
    driver.get('https://httpbin.org/ip')
    time.sleep(2)
    
    print(f"📄 Заголовок: {driver.title}")
    print(f"🌐 URL: {driver.current_url}")
    
    driver.quit()
    print("✅ Тест завершён успешно!")
    
except Exception as e:
    print(f"❌ Ошибка: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
