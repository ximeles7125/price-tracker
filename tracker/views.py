from django.shortcuts import render, redirect
from django.contrib import messages
from django.conf import settings
from .models import Product
from .forms import AddProductForm

# === Константы для монетизации ===
MAX_FREE_PRODUCTS = 5  # Лимит бесплатных товаров
AFFILIATE_REF = 'ref=your_partner_id'  # Твой партнёрский хвостик (замени!)


def add_product(request):
    """
    Страница добавления товара.
    """
    # Для теста: берём Telegram ID из запроса (?tg_id=123456789)
    # В реальном проекте: привязка через команду /start в боте
    telegram_id = request.GET.get('tg_id')

    # Проверяем лимит для бесплатных пользователей
    if telegram_id:
        user_products = Product.objects.filter(
            telegram_id=telegram_id,
            is_active=True
        ).count()

        if user_products >= MAX_FREE_PRODUCTS:
            messages.error(
                request,
                f'❌ Достигнут лимит бесплатных товаров ({MAX_FREE_PRODUCTS}). '
                f'Оформите подписку за 300₽/мес для безлимита!'
            )
            return redirect('tracker:add_product')

    if request.method == 'POST':
        form = AddProductForm(request.POST)
        if form.is_valid():
            product = form.save(commit=False)

            # === МОНЕТИЗАЦИЯ: добавляем партнёрскую ссылку ===
            original_url = product.url
            if AFFILIATE_REF and '?' not in original_url:
                product.url = f"{original_url}?{AFFILIATE_REF}"
            elif AFFILIATE_REF:
                product.url = f"{original_url}&{AFFILIATE_REF}"

            # Сохраняем Telegram ID, если передан
            # if telegram_id: <== было
            #     product.telegram_id = telegram_id <== было

            telegram_id = request.GET.get('tg_id')  # Берём из URL, а не из формы
            if telegram_id and telegram_id.isdigit():  # Проверяем, что это число
                product.telegram_id = int(telegram_id)  # ← Преобразуем в int!
            # Если telegram_id пустой — просто не устанавливаем его (останется None)

            product.save()

            messages.success(
                request,
                f'✅ Товар "{product.name or "Без названия"}" добавлен! '
                f'Уведомление придёт, когда цена станет ≤ {product.target_price} ₽'
            )
            return redirect('tracker:add_product')
    else:
        # form = AddProductForm(initial={'telegram_id': telegram_id}) <== было
        form = AddProductForm()  # ← Убираем initial, он больше не нужен

    # Показываем статистику пользователя
    stats = None
    if telegram_id:
        stats = {
            'used': Product.objects.filter(
                telegram_id=telegram_id,
                is_active=True
            ).count(),
            'limit': MAX_FREE_PRODUCTS,
        }

    return render(request, 'tracker/add_product.html', {
        'form': form,
        'stats': stats,
        'affiliate_info': AFFILIATE_REF,
    })


def home(request):
    """
    Главная страница с краткой инструкцией.
    """
    return render(request, 'tracker/home.html')