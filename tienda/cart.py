from decimal import Decimal
from django.conf import settings
from .models import Producto, ImagenProducto

class Cart:
    def __init__(self, request):
        self.session = request.session
        cart = self.session.get(settings.CART_SESSION_ID)
        if not cart:
            cart = self.session[settings.CART_SESSION_ID] = {}
        self.cart = cart

    def add(self, producto_id, talla, imagen_id, cantidad=1):
        # Llave única que combina producto, talla y la foto exacta seleccionada
        item_key = f"{producto_id}_{talla}_{imagen_id}"

        if item_key not in self.cart:
            producto = Producto.objects.get(id=producto_id)
            self.cart[item_key] = {
                'producto_id': producto_id,
                'talla': talla,
                'imagen_id': imagen_id,
                'cantidad': 0,
                'precio': str(producto.precio_actual)
            }
        self.cart[item_key]['cantidad'] += cantidad
        self.save()

    def remove(self, item_key):
        if item_key in self.cart:
            del self.cart[item_key]
            self.save()

    def save(self):
        self.session.modified = True

    def __iter__(self):
        for item_key, item in self.cart.items():
            producto = Producto.objects.get(id=item['producto_id'])

            # Recuperamos la imagen específica que escogió el usuario
            imagen_seleccionada = None
            if item.get('imagen_id'):
                try:
                    imagen_seleccionada = ImagenProducto.objects.get(id=item['imagen_id'])
                except ImagenProducto.DoesNotExist:
                    imagen_seleccionada = producto.imagen_principal

            precio = Decimal(item['precio'])
            yield {
                'key': item_key,
                'producto': producto,
                'talla': item['talla'],
                'imagen_seleccionada': imagen_seleccionada,
                'precio': precio,
                'cantidad': item['cantidad'],
                'total_precio': precio * item['cantidad']
            }

    def get_total_price(self):
        return sum(Decimal(item['precio']) * item['cantidad'] for item in self.cart.values())

    def __len__(self):
        return sum(item['cantidad'] for item in self.cart.values())

    def clear(self):
        if settings.CART_SESSION_ID in self.session:
            del self.session[settings.CART_SESSION_ID]
            self.save()
