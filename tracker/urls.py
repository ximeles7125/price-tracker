from django.urls import path
from . import views

app_name = 'tracker'

urlpatterns = [
    path('', views.home, name='home'),
    path('add/', views.add_product, name='add_product'),
]