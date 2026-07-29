from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q

from .models import Producto, Marca, ImagenProducto, Orden, ItemOrden
from .cart import Cart


def inicio(request):
    marcas = Marca.objects.all()
    # Optimización de consulta N+1 con select_related y prefetch_related
    productos_destacados = (
        Producto.objects.filter(activo=True)
        .select_related('marca')
        .prefetch_related('imagenes')[:8]
    )
    return render(request, 'tienda/inicio.html', {
        'marcas': marcas,
        'productos': productos_destacados
    })


def catalogo(request, marca_slug=None):
    marcas = Marca.objects.all()
    # Solo productos activos
    productos_list = (
        Producto.objects.filter(activo=True)
        .select_related('marca')
        .prefetch_related('imagenes')
    )
    marca_seleccionada = None

    # 1. Búsqueda por término (nombre, descripción o marca)
    query = request.GET.get('q', '').strip()
    if query:
        productos_list = productos_list.filter(
            Q(nombre__icontains=query) |
            Q(descripcion__icontains=query) |
            Q(marca__nombre__icontains=query)
        )

    # 2. Filtro por Marca si viene slug en la URL
    if marca_slug:
        marca_seleccionada = get_object_or_404(Marca, slug=marca_slug)
        productos_list = productos_list.filter(marca=marca_seleccionada)

    # 3. Ordenamiento por precio
    orden = request.GET.get('orden')
    if orden == 'precio_asc':
        productos_list = productos_list.order_by('precio_regular')
    elif orden == 'precio_desc':
        productos_list = productos_list.order_by('-precio_regular')

    # 4. Paginación (9 productos por página)
    paginator = Paginator(productos_list, 9)
    page_number = request.GET.get('page')
    productos = paginator.get_page(page_number)

    return render(request, 'tienda/catalogo.html', {
        'marcas': marcas,
        'productos': productos,
        'marca_seleccionada': marca_seleccionada,
        'query': query,
        'orden': orden,
    })


def detalle_producto(request, slug):
    producto = get_object_or_404(
        Producto.objects.select_related('marca').prefetch_related('imagenes', 'resenas'),
        slug=slug,
        activo=True
    )
    imagenes = producto.imagenes.all()
    imagen_inicial = producto.imagenes.filter(es_principal=True).first() or producto.imagenes.first()

    return render(request, 'tienda/detalle.html', {
        'producto': producto,
        'imagenes': imagenes,
        'imagen_inicial': imagen_inicial,
    })


# --- Vistas del Carrito de Compras 🛒 ---

def detalle_carrito(request):
    cart = Cart(request)
    subtotal = cart.get_total_price()
    descuento = subtotal * Decimal('0.10') if len(cart) > 0 else Decimal('0.00')
    total_final = subtotal - descuento

    return render(request, 'tienda/carrito.html', {
        'cart': cart,
        'subtotal': subtotal,
        'descuento': descuento,
        'total_final': total_final,
    })


def agregar_al_carrito(request, producto_id):
    if request.method == 'POST':
        cart = Cart(request)

        talla = request.POST.get('talla', '39')
        imagen_id = request.POST.get('imagen_id') or None

        try:
            cantidad = int(request.POST.get('cantidad', 1))
            if cantidad < 1:
                cantidad = 1
        except (ValueError, TypeError):
            cantidad = 1

        cart.add(producto_id=producto_id, talla=talla, imagen_id=imagen_id, cantidad=cantidad)
        messages.success(request, "Producto añadido al carrito.")

    return redirect('tienda:detalle_carrito')


def actualizar_cantidad_carrito(request, item_key):
    """Permite incrementar o decrementar ítems desde el carrito (+ / -)"""
    if request.method == 'POST':
        cart = Cart(request)
        accion = request.POST.get('accion')

        if item_key in cart.cart:
            if accion == 'aumentar':
                cart.cart[item_key]['cantidad'] += 1
            elif accion == 'disminuir':
                if cart.cart[item_key]['cantidad'] > 1:
                    cart.cart[item_key]['cantidad'] -= 1
                else:
                    cart.remove(item_key)
                    return redirect('tienda:detalle_carrito')
            cart.save()

    return redirect('tienda:detalle_carrito')


def eliminar_del_carrito(request, item_key):
    cart = Cart(request)
    cart.remove(item_key)
    messages.info(request, "Producto eliminado del carrito.")
    return redirect('tienda:detalle_carrito')


# --- Checkout con Transacción Atómica 🔒 ---

def checkout(request):
    cart = Cart(request)
    if len(cart) == 0:
        messages.warning(request, "Tu carrito está vacío.")
        return redirect('tienda:catalogo')

    subtotal = cart.get_total_price()
    descuento = subtotal * Decimal('0.10')
    total_final = subtotal - descuento

    if request.method == 'POST':
        # Captura de datos
        nombre_completo = request.POST.get('nombre_completo', '').strip()
        email = request.POST.get('email', '').strip()
        telefono = request.POST.get('telefono', '').strip()
        direccion = request.POST.get('direccion', '').strip()
        ciudad = request.POST.get('ciudad', '').strip()

        # Validar campos vacíos
        if not all([nombre_completo, email, telefono, direccion, ciudad]):
            return render(request, 'tienda/checkout.html', {
                'cart': cart,
                'subtotal': subtotal,
                'descuento': descuento,
                'total_final': total_final,
                'error': "Por favor completa todos los campos de envío."
            })

        # Proceso seguro en base de datos
        try:
            with transaction.atomic():
                # 1. Crear la Orden
                orden = Orden.objects.create(
                    usuario=request.user if request.user.is_authenticated else None,
                    nombre_completo=nombre_completo,
                    email=email,
                    telefono=telefono,
                    direccion=direccion,
                    ciudad=ciudad,
                    costo_envio=Decimal('0.00'),
                    total=total_final,
                    estado='PENDIENTE'
                )

                # 2. Crear los ítems de la orden
                for item in cart:
                    imagen_obj = None
                    if item.get('imagen_id'):
                        imagen_obj = ImagenProducto.objects.filter(id=item['imagen_id']).first()

                    ItemOrden.objects.create(
                        orden=orden,
                        producto=item['producto'],
                        talla=item['talla'],
                        imagen_seleccionada=imagen_obj,
                        precio_unitario=item['precio_unitario'],
                        cantidad=item['cantidad']
                    )

                # 3. Vaciar carrito tras el guardado exitoso
                cart.clear()

                # Renderizar vista de confirmación con los datos creados
                return render(request, 'tienda/confirmacion.html', {'orden': orden})

        except Exception as e:
            messages.error(request, f"Ocurrió un problema guardando tu orden: {str(e)}")
            return redirect('tienda:checkout')

    return render(request, 'tienda/checkout.html', {
        'cart': cart,
        'subtotal': subtotal,
        'descuento': descuento,
        'total_final': total_final,
    })
