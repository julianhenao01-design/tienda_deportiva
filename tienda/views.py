import urllib.parse
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q

from .models import Producto, Marca, ImagenProducto, Orden, ItemOrden
from .cart import Cart

# Configura aquí el número de teléfono de tu tienda (con código de país sin el +)
NUMERO_WHATSAPP_TIENDA = "3058606365"


# --- PÁGINAS PRINCIPALES ---

def inicio(request):
    productos = Producto.objects.all()[:8]
    return render(request, 'tienda/index.html', {'productos': productos})


def catalogo(request, marca_slug=None):
    productos = Producto.objects.all()
    marca = None
    if marca_slug:
        marca = get_object_or_404(Marca, slug=marca_slug)
        productos = productos.filter(marca=marca)
    return render(request, 'tienda/catalogo.html', {'productos': productos, 'marca': marca})


def detalle_producto(request, slug):
    producto = get_object_or_404(Producto, slug=slug)
    return render(request, 'tienda/detalle_producto.html', {'producto': producto})


# --- CARRITO DE COMPRAS 🛒 ---

def detalle_carrito(request):
    cart = Cart(request)
    return render(request, 'tienda/carrito.html', {'cart': cart})


def agregar_al_carrito(request, producto_id):
    cart = Cart(request)
    producto = get_object_or_404(Producto, id=producto_id)
    talla = request.POST.get('talla', '')
    imagen_id = request.POST.get('imagen_id', None)
    cart.add(producto=producto, cantidad=1, talla=talla, imagen_id=imagen_id)
    return redirect('tienda:detalle_carrito')


def actualizar_cantidad_carrito(request, item_key):
    cart = Cart(request)
    cantidad = int(request.POST.get('cantidad', 1))
    cart.update_quantity(item_key, cantidad)
    return redirect('tienda:detalle_carrito')


def eliminar_del_carrito(request, item_key):
    cart = Cart(request)
    cart.remove(item_key)
    return redirect('tienda:detalle_carrito')


# --- PROCESO DE PAGO Y WHATSAPP 💳 ---

def checkout(request):
    cart = Cart(request)
    if len(cart) == 0:
        messages.warning(request, "Tu carrito está vacío.")
        return redirect('tienda:catalogo')

    subtotal = cart.get_total_price()
    descuento = subtotal * Decimal('0.10')
    total_final = subtotal - descuento

    if request.method == 'POST':
        nombre_completo = request.POST.get('nombre_completo', '').strip()
        email = request.POST.get('email', '').strip()
        telefono = request.POST.get('telefono', '').strip()
        direccion = request.POST.get('direccion', '').strip()
        ciudad = request.POST.get('ciudad', '').strip()

        if not all([nombre_completo, email, telefono, direccion, ciudad]):
            return render(request, 'tienda/checkout.html', {
                'cart': cart,
                'subtotal': subtotal,
                'descuento': descuento,
                'total_final': total_final,
                'error': "Por favor completa todos los campos de envío."
            })

        try:
            with transaction.atomic():
                # 1. Crear Registro de la Orden
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

                # 2. Guardar Ítems y armar texto de productos para WhatsApp
                lineas_productos = []
                for item in cart:
                    imagen_obj = None
                    if item.get('imagen_id'):
                        imagen_obj = ImagenProducto.objects.filter(id=item['imagen_id']).first()

                    item_orden = ItemOrden.objects.create(
                        orden=orden,
                        producto=item['producto'],
                        talla=item['talla'],
                        imagen_seleccionada=imagen_obj,
                        precio_unitario=item['precio_unitario'],
                        cantidad=item['cantidad']
                    )
                    lineas_productos.append(
                        f"• {item_orden.cantidad}x {item_orden.producto.nombre} (Talla: {item_orden.talla})"
                    )

                # 3. Vaciar carrito de la sesión
                cart.clear()

                # 4. Construir el mensaje pre-armado para WhatsApp
                texto_productos = "\n".join(lineas_productos)

                mensaje_wa = (
                    f"👋 *¡Hola DUAL SHOES! Acabo de realizar un pedido en la tienda web.*\n\n"
                    f"📌 *NÚMERO DE PEDIDO:* #{orden.id}\n"
                    f"👤 *Cliente:* {orden.nombre_completo}\n"
                    f"📱 *Teléfono:* {orden.telefono}\n"
                    f"📍 *Ciudad:* {orden.ciudad}\n"
                    f"🏠 *Dirección:* {orden.direccion}\n\n"
                    f"👟 *PRODUCTOS SOLICITADOS:*\n{texto_productos}\n\n"
                    f"💰 *TOTAL A PAGAR:* $ {orden.total:,.0f} COP\n\n"
                    f"Quedo atento a las instrucciones para el pago y el envío de la guía. ¡Muchas gracias!"
                )

                mensaje_encoded = urllib.parse.quote(mensaje_wa)
                whatsapp_url = f"https://wa.me/{NUMERO_WHATSAPP_TIENDA}?text={mensaje_encoded}"

                return render(request, 'tienda/confirmacion.html', {
                    'orden': orden,
                    'whatsapp_url': whatsapp_url
                })

        except Exception as e:
            messages.error(request, f"Ocurrió un problema guardando tu orden: {str(e)}")
            return redirect('tienda:checkout')

    return render(request, 'tienda/checkout.html', {
        'cart': cart,
        'subtotal': subtotal,
        'descuento': descuento,
        'total_final': total_final,
    })
