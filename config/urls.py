from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('tracker.urls')),  # ← Наша главная страница
    path('tracker/', include('tracker.urls')),  # ← Все страницы трекера
]