from django.urls import path
from . import views

app_name = 'tienda'

urlpatterns = [
    path('', views.inicio, name='inicio'),
    path('catalogo/', views.catalogo, name='catalogo'),
    path('catalogo/<slug:marca_slug>/', views.catalogo, name='catalogo_marca'),
    path('producto/<slug:slug>/', views.detalle_producto, name='detalle_producto'),
]
