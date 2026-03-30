from django import forms
from .models import Product


class AddProductForm(forms.ModelForm):
    """
    Простая форма для добавления товара пользователем.
    """

    # # Поле для Telegram ID (скрытое, заполняется автоматически)
    # telegram_id = forms.CharField(
    #     widget=forms.HiddenInput(),
    #     required=False
    # )


    class Meta:
        model = Product
        # fields = ['url', 'target_price', 'telegram_id']
        fields = ['url', 'target_price'] # ← Убрали telegram_id отсюда!
        widgets = {
            'url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://www.wildberries.ru/catalog/...',
                'required': True
            }),
            'target_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '5000',
                'step': '0.01',
                'min': '0',
                'required': True
            }),
        }
        labels = {
            'url': 'Ссылка на товар',
            'target_price': 'Желаемая цена (₽)',
        }
        help_texts = {
            'url': 'Пришли ссылку на товар',
            'target_price': 'При достижении этой цены придёт уведомление',
        }