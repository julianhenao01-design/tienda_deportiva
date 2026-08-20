# -*- coding: utf-8 -*-
import urllib.parse
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction
from django.contrib import messages

from .models import Producto, Marca, ImagenProducto, Orden, ItemOrden
from .cart import Cart

# Configura aquí el número de teléfono de tu tienda (con código de país sin el +)
NUMERO_WHATSAPP_TIENDA = "3058606365"


# --- PÁGINAS PRINCIPALES ---

def inicio(request):
    marcas = Marca.objects.all()
    return render(request, 'tienda/inicio.html', {'marcas': marcas})


def catalogo(request, marca_slug=None):
    productos = Producto.objects.filter(activo=True)
    marcas = Marca.objects.all()
    marca_seleccionada = None

    if marca_slug:
        marca_seleccionada = get_object_or_404(Marca, slug=marca_slug)
        productos = productos.filter(marca=marca_seleccionada)

    return render(request, 'tienda/catalogo.html', {
        'productos': productos,
        'marcas': marcas,
        'marca_seleccionada': marca_seleccionada
    })


def detalle_producto(request, slug):
    producto = get_object_or_404(Producto, slug=slug, activo=True)
    imagen_inicial = producto.imagenes.filter(es_principal=True).first() or producto.imagenes.first()

    return render(request, 'tienda/detalle.html', {
        'producto': producto,
        'imagen_inicial': imagen_inicial
    })


# --- CARRITO DE COMPRAS 🛒 ---

def detalle_carrito(request):
    cart = Cart(request)
    return render(request, 'tienda/carrito.html', {'cart': cart})


def agregar_al_carrito(request, producto_id):
    cart = Cart(request)
    producto = get_object_or_404(Producto, id=producto_id)
    talla = request.POST.get('talla', '39')
    imagen_id = request.POST.get('imagen_id', None)

    try:
        cantidad = int(request.POST.get('cantidad', 1))
    except (ValueError, TypeError):
        cantidad = 1

    cart.add(
        producto_id=producto.id,
        talla=talla,
        imagen_id=imagen_id,
        cantidad=cantidad
    )
    return redirect('tienda:detalle_carrito')


def actualizar_cantidad_carrito(request, item_key):
    cart = Cart(request)
    try:
        cantidad = int(request.POST.get('cantidad', 1))
    except (ValueError, TypeError):
        cantidad = 1

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

                # 2. Guardar Ítems y armar texto con enlaces a las imágenes
                lineas_productos = []
                for item in cart:
                    imagen_obj = item.get('imagen_seleccionada')

                    item_orden = ItemOrden.objects.create(
                        orden=orden,
                        producto=item['producto'],
                        talla=item['talla'],
                        imagen_seleccionada=imagen_obj,
                        precio_unitario=item['precio'],
                        cantidad=item['cantidad']
                    )

                    # CONSTRUCCIÓN DE LA URL ABSOLUTA DE LA IMAGEN 📸
                    url_imagen = ""
                    if imagen_obj and imagen_obj.imagen:
                        url_imagen = request.build_absolute_uri(imagen_obj.imagen.url)
                    elif item_orden.producto.imagen_principal:
                        url_imagen = request.build_absolute_uri(item_orden.producto.imagen_principal.url)

                    texto_foto = f"\n   🖼️ Ver Foto: {url_imagen}" if url_imagen else ""

                    lineas_productos.append(
                        f"• {item_orden.cantidad}x {item_orden.producto.nombre} (Talla: {item_orden.talla}){texto_foto}"
                    )

                # 3. Vaciar carrito de la sesión
                cart.clear()

                # 4. Construir el mensaje pre-armado para WhatsApp
                texto_productos = "\n\n".join(lineas_productos)

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

                # Encodificación UTF-8 explícita para WhatsApp
                mensaje_encoded = urllib.parse.quote(mensaje_wa.encode('utf-8'))
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
