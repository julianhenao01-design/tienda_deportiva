from django.contrib import admin
from django.utils.safestring import mark_safe
from unfold.admin import ModelAdmin, TabularInline
from .models import Marca, Producto, ImagenProducto, Resena, Orden, ItemOrden


# Inline para gestión de fotos con tarjetas modernas y vista previa
class ImagenProductoInline(TabularInline):
    model = ImagenProducto
    extra = 1
    fields = ('vista_previa', 'imagen', 'es_principal')
    readonly_fields = ('vista_previa',)

    @admin.display(description="Vista Previa")
    def vista_previa(self, obj):
        if obj and obj.imagen:
            return mark_safe(
                f'<img src="{obj.imagen.url}" style="width: 60px; height: 60px; object-fit: contain; border-radius: 8px; background: #f8fafc; border: 1px solid #e2e8f0; padding: 2px;" />'
            )
        return "Sin foto"


@admin.register(Marca)
class MarcaAdmin(ModelAdmin):
    list_display = ('nombre', 'slug', 'vista_logo')
    prepopulated_fields = {'slug': ('nombre',)}

    @admin.display(description="Logo")
    def vista_logo(self, obj):
        if obj and obj.logo:
            return mark_safe(f'<img src="{obj.logo.url}" style="height: 32px; object-fit: contain;" />')
        return "-"


@admin.register(Producto)
class ProductoAdmin(ModelAdmin):
    list_display = ('nombre', 'marca', 'precio_regular', 'precio_oferta')
    list_filter = ('marca',)
    search_fields = ('nombre', 'descripcion')
    prepopulated_fields = {'slug': ('nombre',)}
    inlines = [ImagenProductoInline]


@admin.register(Resena)
class ResenaAdmin(ModelAdmin):
    list_display = ('producto', 'nombre_cliente', 'calificacion', 'fecha')
    list_filter = ('calificacion', 'fecha')


class ItemOrdenInline(TabularInline):
    model = ItemOrden
    extra = 0
    readonly_fields = ('producto', 'talla', 'imagen_seleccionada', 'precio_unitario', 'cantidad')
    can_delete = False


@admin.register(Orden)
class OrdenAdmin(ModelAdmin):
    list_display = ('id', 'nombre_completo', 'email', 'total', 'estado', 'fecha_creacion')
    list_filter = ('estado', 'fecha_creacion')
    search_fields = ('nombre_completo', 'email', 'id')
    inlines = [ItemOrdenInline]
