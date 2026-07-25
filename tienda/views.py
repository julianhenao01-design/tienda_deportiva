from django.shortcuts import render, redirect, get_object_or_404
from .models import Producto, Marca
from .cart import Cart

def inicio(request):
    marcas = Marca.objects.all()
    # Eliminamos el filtro (agotado=False) porque retiramos el control de stock
    productos_destacados = Producto.objects.all()[:8]
    return render(request, 'tienda/inicio.html', {
        'marcas': marcas,
        'productos': productos_destacados
    })


def catalogo(request, marca_slug=None):
    marcas = Marca.objects.all()
    # Eliminamos el filtro (agotado=False)
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
    # Asegúrate de que el nombre de tu plantilla aquí coincida con el archivo real (detalle.html o detalle_producto.html)
    return render(request, 'tienda/detalle.html', {
        'producto': producto
    })


# --- Vistas del Carrito de Compras 🛒 ---

def detalle_carrito(request):
    cart = Cart(request)
    return render(request, 'tienda/carrito.html', {'cart': cart})


def agregar_al_carrito(request, producto_id):
    cart = Cart(request)

    # 1. Capturamos la talla (39 por defecto si no viene)
    talla = request.POST.get('talla', '39')

    # 2. Capturamos la foto exacta seleccionada
    imagen_id = request.POST.get('imagen_id')

    # 3. Cantidad
    cantidad = int(request.POST.get('cantidad', 1))

    # Pasamos las nuevas variables al Carrito en lugar del variante_id
    cart.add(producto_id=producto_id, talla=talla, imagen_id=imagen_id, cantidad=cantidad)

    return redirect('tienda:detalle_carrito')


def eliminar_del_carrito(request, item_key):
    cart = Cart(request)
    cart.remove(item_key)
    return redirect('tienda:detalle_carrito')


def checkout(request):
    cart = Cart(request)
    if len(cart) == 0:
        return redirect('tienda:catalogo')

    if request.method == 'POST':
        # Aquí guardarás la orden en la base de datos
        cart.clear()
        return render(request, 'tienda/confirmacion.html')

    return render(request, 'tienda/checkout.html', {'cart': cart})
