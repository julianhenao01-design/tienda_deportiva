from decimal import Decimal
from django.conf import settings
from .models import Producto, VarianteProducto

class Cart:
    def __init__(self, request):
        self.session = request.session
        cart = self.session.get(settings.CART_SESSION_ID)
        if not cart:
            cart = self.session[settings.CART_SESSION_ID] = {}
        self.cart = cart

    def add(self, producto_id, variante_id=None, cantidad=1):
        item_key = f"{producto_id}_{variante_id}" if variante_id else str(producto_id)
        if item_key not in self.cart:
            self.cart[item_key] = {
                'producto_id': producto_id,
                'variante_id': variante_id,
                'cantidad': 0,
                'precio': str(Producto.objects.get(id=producto_id).precio_regular)
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
            variante = VarianteProducto.objects.get(id=item['variante_id']) if item['variante_id'] else None

            precio = Decimal(item['precio'])
            yield {
                'key': item_key,
                'producto': producto,
                'variante': variante,
                'precio': precio,
                'cantidad': item['cantidad'],
                'total_precio': precio * item['cantidad']
            }

    def get_total_price(self):
        return sum(Decimal(item['precio']) * item['cantidad'] for item in self.cart.values())

    def __len__(self):
        return sum(item['cantidad'] for item in self.cart.values())

    def clear(self):
        del self.session[settings.CART_SESSION_ID]
        self.save()
