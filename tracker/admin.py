from django.contrib import admin
from .models import Product

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """
    Настройка отображения модели Product в админке Django
    """

    # Какие поля показывать в списке товаров
    list_display = (
        'name',
        'url',
        'current_price',
        'target_price',
        'is_active',
        'created_at'
    )

    # Какие поля можно редактировать прямо в списке
    list_editable = ('is_active',)

    # Фильтры справа (можно фильтровать по статусу)
    list_filter = ('is_active', 'created_at')

    # Поиск по названию и URL
    search_fields = ('name', 'url')

    # Поля, которые нельзя редактировать (только чтение)
    readonly_fields = ('created_at', 'updated_at', 'current_price')

    # Как группировать поля в форме редактирования
    fieldsets = (
        ('Основная информация',{
            'fields': ('url', 'name', 'target_price')
        }),
        ('Статус и цены', {
            'fields': ('current_price', 'is_active', 'telegram_id')
        }),
        ('Даты', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',) # Сворачиваемая секция
        }),
    )