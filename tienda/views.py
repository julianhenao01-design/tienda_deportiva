from django.shortcuts import render, get_object_or_404
from .models import Producto, Marca

def inicio(request):
    marcas = Marca.objects.all()
    productos_destacados = Producto.objects.filter(agotado=False)[:8]
    return render(request, 'tienda/inicio.html', {
        'marcas': marcas,
        'productos': productos_destacados
    })

def catalogo(request, marca_slug=None):
    marcas = Marca.objects.all()
    productos = Producto.objects.filter(agotado=False)
    marca_seleccionada = None

    if marca_slug:
        marca_seleccionada = get_object_or_404(Marca, slug=marca_slug)
        productos = productos.filter(marca=marca_seleccionada)

    return render(request, 'tienda/catalogo.html', {
        'marcas': marcas,
        'productos': productos,
        'marca_seleccionada': marca_seleccionada
    })

def detalle_producto(request, slug):
    producto = get_object_or_404(Producto, slug=slug)
    return render(request, 'tienda/detalle.html', {
        'producto': producto
    })
