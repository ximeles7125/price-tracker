#!/usr/bin/env python
"""Тесты для функции _extract_price"""
import re
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def _extract_price(text: str):
    """Копия функции из wb.py для тестов"""
    if not text:
        return None
    try:
        text = str(text).strip()
        text = re.sub(r'[\s\u00a0\u202f\u2009]+', ' ', text)
        dots = text.count('.')
        commas = text.count(',')
        raw_cleaned = re.sub(r'[^\d.,]', '', text)
        cleaned = raw_cleaned
        
        if dots == 1 and commas == 1:
            if text.index(',') < text.index('.'):
                cleaned = cleaned.replace(',', '')
            else:
                cleaned = cleaned.replace('.', '').replace(',', '.')
        elif commas == 1 and dots == 0:
            parts = cleaned.split(',')
            if len(parts) == 2 and len(parts[1]) <= 2:
                cleaned = cleaned.replace(',', '.')
            else:
                cleaned = cleaned.replace(',', '')
        elif commas > 1:
            cleaned = cleaned.replace(',', '')
        
        if cleaned:
            price = float(cleaned)
            if 0 < price < 10_000_000:
                return price
    except:
        pass
    return None

# === ТЕСТЫ ===
test_cases = [
    ("1 000 ₽", 1000.0),
    ("12 999 ₽", 12999.0),
    ("1 299,99 ₽", 1299.99),
    ("1,299.50", 1299.5),
    ("1299", 1299.0),
    ("1\xa0000 ₽", 1000.0),  # неразрывный пробел
    ("999 ₽", 999.0),
    ("1 000 000 ₽", 1000000.0),
    ("", None),
    ("бесплатно", None),
]

print("🧪 Тестируем _extract_price:")
print("=" * 50)
all_passed = True
for input_val, expected in test_cases:
    result = _extract_price(input_val)
    status = "✅" if result == expected else "❌"
    if result != expected:
        all_passed = False
    print(f"{status} '{input_val}' → {result} (ожидалось: {expected})")

print("=" * 50)
if all_passed:
    print("🎉 Все тесты пройдены!")
else:
    print("⚠️ Есть неудачные тесты — проверь логи выше")
