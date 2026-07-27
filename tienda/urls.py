from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'tienda'

urlpatterns = [
    # Páginas principales
    path('', views.inicio, name='inicio'),
    path('catalogo/', views.catalogo, name='catalogo'),
    path('catalogo/<slug:marca_slug>/', views.catalogo, name='catalogo_marca'),
    path('producto/<slug:slug>/', views.detalle_producto, name='detalle_producto'),

    # Carrito de Compras 🛒
    path('carrito/', views.detalle_carrito, name='detalle_carrito'),
    path('carrito/agregar/<int:producto_id>/', views.agregar_al_carrito, name='agregar_al_carrito'),
    path('carrito/eliminar/<str:item_key>/', views.eliminar_del_carrito, name='eliminar_del_carrito'),

    # Proceso de Pago 💳
    path('checkout/', views.checkout, name='checkout'),

    # Autenticación de Usuarios 🔐
    path('login/', auth_views.LoginView.as_view(template_name='tienda/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='tienda:inicio'), name='logout'),
]