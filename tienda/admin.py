from django.contrib import admin
from .models import Marca, Producto, ImagenProducto, Resena, Orden, ItemOrden


# Permitir agregar múltiples imágenes directo desde la pantalla del Producto
class ImagenProductoInline(admin.TabularInline):
    model = ImagenProducto
    extra = 1


@admin.register(Marca)
class MarcaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'slug')
    prepopulated_fields = {'slug': ('nombre',)}


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    # Se remueve 'agotado' de list_display y list_filter
    list_display = ('nombre', 'marca', 'precio_regular', 'precio_oferta')
    list_filter = ('marca',)
    search_fields = ('nombre', 'descripcion')
    prepopulated_fields = {'slug': ('nombre',)}
    inlines = [ImagenProductoInline]


@admin.register(Resena)
class ResenaAdmin(admin.ModelAdmin):
    list_display = ('producto', 'nombre_cliente', 'calificacion', 'fecha')
    list_filter = ('calificacion', 'fecha')


class ItemOrdenInline(admin.TabularInline):
    model = ItemOrden
    extra = 0
    # Muestra los nuevos campos del item de orden (talla y foto seleccionada)
    readonly_fields = ('producto', 'talla', 'imagen_seleccionada', 'precio_unitario', 'cantidad')


@admin.register(Orden)
class OrdenAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre_completo', 'email', 'total', 'estado', 'fecha_creacion')
    list_filter = ('estado', 'fecha_creacion')
    search_fields = ('nombre_completo', 'email', 'id')
    inlines = [ItemOrdenInline]