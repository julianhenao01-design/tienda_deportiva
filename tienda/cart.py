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
            try:
                producto = Producto.objects.get(id=producto_id)
            except Producto.DoesNotExist:
                return  # Si el producto no existe en BD, cancelamos silenciosamente

            # Obtenemos el precio en oferta o regular
            precio_val = getattr(producto, 'precio_oferta', None) or producto.precio_regular

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
        # 1. Obtenemos todos los IDs de productos que hay en la sesión
        product_ids = [item['producto_id'] for item in self.cart.values()]

        # 2. Consultamos la base de datos de una sola vez en bloque (in_bulk)
        productos = Producto.objects.in_bulk(product_ids)

        keys_to_remove = []

        # 3. Recorremos el carrito verificando existencia
        for item_key, item in list(self.cart.items()):
            producto_id = item['producto_id']

            # Si el producto fue eliminado del panel Admin, marcamos la clave para borrarla de la sesión
            if producto_id not in productos:
                keys_to_remove.append(item_key)
                continue

            producto = productos[producto_id]

            # Recuperamos la imagen específica y su color
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

            # Extraemos el nombre del color de forma segura
            color_nombre = None
            if imagen_seleccionada and hasattr(imagen_seleccionada, 'color_nombre'):
                color_nombre = imagen_seleccionada.color_nombre

            precio = Decimal(item['precio'])
            yield {
                'key': item_key,
                'producto': producto,
                'talla': item['talla'],
                'color': color_nombre,  # <-- ¡NUEVO! Obtenemos el nombre del color
                'imagen_seleccionada': imagen_seleccionada,
                'precio': precio,
                'cantidad': item['cantidad'],
                'total_precio': precio * item['cantidad']
            }

        # 4. Limpiamos automáticamente la sesión si había productos huérfanos
        if keys_to_remove:
            for key in keys_to_remove:
                del self.cart[key]
            self.save()

    def get_total_price(self):
        # Calcula el total iterando directamente sobre los ítems válidos
        return sum(item['total_precio'] for item in self)

    def __len__(self):
        return sum(item['cantidad'] for item in self.cart.values())

    def clear(self):
        if settings.CART_SESSION_ID in self.session:
            del self.session[settings.CART_SESSION_ID]
            self.save()
