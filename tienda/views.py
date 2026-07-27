from django.shortcuts import render, redirect, get_object_or_404
from .models import Producto, Marca
from .cart import Cart

def inicio(request):
    marcas = Marca.objects.all()
    productos_destacados = Producto.objects.all()[:8]
    return render(request, 'tienda/inicio.html', {
        'marcas': marcas,
        'productos': productos_destacados
    })


def catalogo(request, marca_slug=None):
    marcas = Marca.objects.all()
    productos = Producto.objects.all()
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
    imagenes = producto.imagenes.all()

    # Imagen principal o primera como inicial
    imagen_inicial = producto.imagenes.filter(es_principal=True).first() or producto.imagenes.first()

    return render(request, 'tienda/detalle.html', {  # <-- Corregido a 'tienda/detalle.html'
        'producto': producto,
        'imagenes': imagenes,
        'imagen_inicial': imagen_inicial,
    })


# --- Vistas del Carrito de Compras 🛒 ---

def detalle_carrito(request):
    cart = Cart(request)
    return render(request, 'tienda/carrito.html', {'cart': cart})


def agregar_al_carrito(request, producto_id):
    cart = Cart(request)

    # 1. Capturamos la talla (39 por defecto si no viene)
    talla = request.POST.get('talla', '39')

    # 2. Capturamos la foto exacta seleccionada (aseguramos None si llega cadena vacía)
    imagen_id = request.POST.get('imagen_id')
    if not imagen_id:
        imagen_id = None

    # 3. Cantidad solicitada
    try:
        cantidad = int(request.POST.get('cantidad', 1))
    except (ValueError, TypeError):
        cantidad = 1

    # Agregamos al carrito guardando la referencia exacta
    cart.add(producto_id=producto_id, talla=talla, imagen_id=imagen_id, cantidad=cantidad)

    return redirect('tienda:detalle_carrito')


def eliminar_del_carrito(request, item_key):
    cart.remove(item_key)
    return redirect('tienda:detalle_carrito')


def checkout(request):
    cart = Cart(request)
    if len(cart) == 0:
        return redirect('tienda:catalogo')

    if request.method == 'POST':
        cart.clear()
        return render(request, 'tienda/confirmacion.html')

    return render(request, 'tienda/checkout.html', {'cart': cart})
