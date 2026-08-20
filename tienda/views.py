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
NUMERO_WHATSAPP_TIENDA = "573000000000"  # Cambia esto por tu número real (ej: 573101234567)


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
