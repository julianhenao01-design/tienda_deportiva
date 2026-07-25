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

    def add(self, producto_id, talla, imagen_id=None, cantidad=1):
        # Generamos una clave única según producto, talla e imagen seleccionada
        img_id_str = str(imagen_id) if imagen_id and str(imagen_id).isdigit() else 'default'
        item_key = f"{producto_id}_{talla}_{img_id_str}"

        if item_key not in self.cart:
            producto = Producto.objects.get(id=producto_id)

            # Obtenemos el precio actual o el precio regular como respaldo
            precio_val = getattr(producto, 'precio_actual', getattr(producto, 'precio_oferta', producto.precio_regular))
            if not precio_val:
                precio_val = producto.precio_regular

            self.cart[item_key] = {
                'producto_id': producto_id,
                'talla': talla,
                'imagen_id': img_id_str,
                'cantidad': 0,
                'precio': str(precio_val)
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
            imagen_id = item.get('imagen_id')

            if imagen_id and str(imagen_id).isdigit():
                try:
                    imagen_seleccionada = ImagenProducto.objects.get(id=int(imagen_id))
                except ImagenProducto.DoesNotExist:
                    imagen_seleccionada = None

            # Fallbacks seguros en caso de que no haya imagen_id o se haya eliminado
            if not imagen_seleccionada:
                if hasattr(producto, 'imagen_principal') and producto.imagen_principal:
                    imagen_seleccionada = producto.imagen_principal
                elif hasattr(producto, 'imagenes') and producto.imagenes.exists():
                    imagen_seleccionada = producto.imagenes.first()

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
