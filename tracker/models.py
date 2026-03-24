from django.db import models

class Product(models.Model):
    url = models.URLField(verbose_name="Ссылка на товар")
    name = models.CharField(max_length=255, blank=True, null=True, verbose_name="Название")
    current_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    target_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Желаемая цена")

    # Для уведомлений
    telegram_id = models.BigIntegerField(verbose_name="Telegram ID пользователя")
    is_active = models.BooleanField(default=True, verbose_name="Активен")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name}({self.current_price} ₽)"

    class Meta:
        verbose_name = "Товар"
        verbose_name_plural = "Товары"

    
