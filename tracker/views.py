from django.shortcuts import render, redirect
from django.contrib import messages
from django.conf import settings
from .models import Product
from .forms import AddProductForm

# === Константы для монетизации ===
MAX_FREE_PRODUCTS = 5  # Лимит бесплатных товаров
# УБРАЛИ: AFFILIATE_REF — партнёрских ссылок не будет


def add_product(request):
    """
    Страница добавления товара.
    """
    # Для теста: берём Telegram ID из запроса (?tg_id=123456789)
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

            # === УБРАЛИ партнёрскую ссылку ===
            # Просто сохраняем URL как есть
            final_url = product.url

            # Сохраняем Telegram ID, если передан
            if telegram_id and telegram_id.isdigit():
                product.telegram_id = int(telegram_id)

            # Обновляем URL и сохраняем
            product.url = final_url
            product.save()

            messages.success(
                request,
                f'✅ Товар "{product.name or "Без названия"}" добавлен! '
                f'Уведомление придёт, когда цена станет ≤ {product.target_price} ₽'
            )
            return redirect('tracker:add_product')
    else:
        form = AddProductForm()

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
    })


def home(request):
    """
    Главная страница с краткой инструкцией.
    """
    return render(request, 'tracker/home.html')