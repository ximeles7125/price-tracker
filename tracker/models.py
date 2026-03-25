from django.db import models

class Product(models.Model):
    """
    Модель товара для отслеживания цены.
    Хранит ссылку на товар, текущую цену
    и желаемую цену пользователя.
    """

    # ссылка на товар (ozon/wb)
    url = models.URLField(
        verbose_name="ссылка на товар",
        max_length=500,
        help_text="Полная ссылка на страницу товара"
    )

    # Название товара (заполнится автоматически при парсинге)
    name = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Название товара",
        help_text="Название заполнится автоматически"
    )

    # Текущая цена (обновляется парсером)
    current_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Текущая цена",
        help_text="Цена в рублях"
    )

    # Желаемая цена пользователя
    target_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Желаемая цена",
        help_text="При достижении этой цены придет уведомление"
    )

    # ID пользователя в Телеграм (для отправки уведомлений)
    telegram_id = models.BigIntegerField(
        verbose_name="Telegram ID пользователя",
        null=True,
        blank=True,
        help_text="ID пользователя для уведомлений"
    )

    # Статус: активен ли товар для отслеживания
    is_active = models.BooleanField(
        default=True,
        verbose_name="Активен",
        help_text="Если выключено, товар не отслеживается"
    )

    # Даты создания и обновления (автоматически)
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата добавления"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Дата обновления"
    )

    def __str__(self):
        """Как будет отображатсья товар в админке и консоли"""
        return f"{self.name or 'Без названия'} - {self.current_price or '?'} ₽"

    class Meta:
        """Настройки отображения в админке"""
        verbose_name = "Товар"
        verbose_name_plural = "Товары"
        ordering = ["-created_at"] # Новые товары отображаются сверху