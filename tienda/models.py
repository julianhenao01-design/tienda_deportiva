from django.db import models
from django.contrib.auth.models import User

# 1. Catálogos individuales por Marca (Nike, Adidas, Puma, etc.)
class Marca(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    descripcion = models.TextField(blank=True)
    logo = models.ImageField(upload_to='marcas/', blank=True, null=True)

    def __str__(self):
        return self.nombre


# 2. Productos (Calzado / Ropa)
class Producto(models.Model):
    marca = models.ForeignKey(Marca, on_delete=models.CASCADE, related_name='productos')
    nombre = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    descripcion = models.TextField()
    precio_regular = models.DecimalField(max_digits=10, decimal_places=2)
    precio_oferta = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    agotado = models.BooleanField(default=False)
    video = models.FileField(upload_to='productos/videos/', blank=True, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    @property
    def precio_actual(self):
        return self.precio_oferta if self.precio_oferta else self.precio_regular

    # --- PROPIEDAD CLAVE PARA RENDERIZAR LA IMAGEN EN EL CATÁLOGO ---
    @property
    def imagen_principal(self):
        """
        Busca primero la foto marcada como 'es_principal'.
        Si no hay ninguna principal marcada, toma la primera disponible de la galería.
        """
        img_principal = self.imagenes.filter(es_principal=True).first()
        if img_principal:
            return img_principal.imagen

        primera_img = self.imagenes.first()
        if primera_img:
            return primera_img.imagen

        return None

    def __str__(self):
        return f"{self.nombre} ({self.marca.nombre})"


# 3. Imágenes múltiples por Producto
class ImagenProducto(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='imagenes')
    imagen = models.ImageField(upload_to='productos/imagenes/')
    es_principal = models.BooleanField(default=False)

    def __str__(self):
        return f"Imagen de {self.producto.nombre}"


# 4. Variantes: Colores (para botones) y Tallas
class VarianteProducto(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='variantes')
    color_nombre = models.CharField(max_length=50) # Ej: Rojo, Negro/Blanco
    color_hex = models.CharField(max_length=7, default='#000000') # Ej: #FF0000
    talla = models.CharField(max_length=10) # Ej: 39, 40, US 9
    stock = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.producto.nombre} - {self.color_nombre} - Talla {self.talla}"


# 5. Comentarios y Experiencia con la Marca/Producto
class Resena(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='resenas')
    nombre_cliente = models.CharField(max_length=100)
    comentario = models.TextField()
    calificacion = models.PositiveIntegerField(default=5) # 1 a 5 estrellas
    fecha = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Reseña de {self.nombre_cliente} en {self.producto.nombre}"


# 6. Ordenes / Pedidos (Flujo Pre-Pago y Envíos Gratis)
class Orden(models.Model):
    ESTADOS = (
        ('PENDIENTE', 'Pendiente de Validación en Bodega'),
        ('CONFIRMADO', 'Stock Confirmado (Listo para Pagar)'),
        ('RECHAZADO', 'Sin Stock en Bodega'),
        ('PAGADO', 'Pago Recibido'),
        ('ENVIADO', 'Pedido Enviado'),
    )

    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    nombre_completo = models.CharField(max_length=150)
    email = models.EmailField()
    telefono = models.CharField(max_length=20)
    direccion = models.CharField(max_length=255)
    ciudad = models.CharField(max_length=100)

    aplico_descuento_registro = models.BooleanField(default=False)
    costo_envio = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='PENDIENTE')
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Orden #{self.id} - {self.nombre_completo} ({self.estado})"


class ItemOrden(models.Model):
    orden = models.ForeignKey(Orden, on_delete=models.CASCADE, related_name='items')
    variante = models.ForeignKey(VarianteProducto, on_delete=models.PROTECT)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    cantidad = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.cantidad}x {self.variante.producto.nombre} ({self.variante.color_nombre} - Talla {self.variante.talla})"