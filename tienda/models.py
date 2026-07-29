from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator


class Marca(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True, db_index=True)
    descripcion = models.TextField(blank=True)
    logo = models.ImageField(upload_to='marcas/', blank=True, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Marca'
        verbose_name_plural = 'Marcas'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    marca = models.ForeignKey(Marca, on_delete=models.CASCADE, related_name='productos')
    nombre = models.CharField(max_length=200, db_index=True)
    slug = models.SlugField(unique=True, db_index=True)
    descripcion = models.TextField()
    precio_regular = models.DecimalField(max_digits=12, decimal_places=2)
    precio_oferta = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    activo = models.BooleanField(default=True, db_index=True, help_text="Indica si el producto se muestra en la tienda.")
    fecha_creacion = models.DateTimeField(auto_now_add=True, db_index=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Producto'
        verbose_name_plural = 'Productos'
        ordering = ['-fecha_creacion']

    @property
    def precio_actual(self):
        return self.precio_oferta if self.precio_oferta else self.precio_regular

    @property
    def imagen_principal(self):
        img_principal = self.imagenes.filter(es_principal=True).first()
        if img_principal:
            return img_principal.imagen
        primera_img = self.imagenes.first()
        if primera_img:
            return primera_img.imagen
        return None

    # Muestra únicamente las fotos que representan una variante de color activa
    @property
    def opciones_color(self):
        return self.imagenes.exclude(color_nombre__isnull=True).exclude(color_nombre='')

    def __str__(self):
        return f"{self.nombre} ({self.marca.nombre})"


class ImagenProducto(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='imagenes')
    imagen = models.ImageField(upload_to='productos/imagenes/')
    color_nombre = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="OPCIONAL: Nombre del color (ej: Verde, Negro). Llena esto SOLO si esta foto es la muestra de una variante de color en el panel derecho. Para fotos normales de la galería o ángulos, DÉJALO EN BLANCO."
    )
    es_principal = models.BooleanField(default=False, db_index=True)
    orden = models.PositiveIntegerField(default=0, help_text="Orden de aparición en la galería.")

    class Meta:
        verbose_name = 'Imagen de Producto'
        verbose_name_plural = 'Imágenes de Productos'
        ordering = ['orden', 'id']

    def __str__(self):
        color_str = f" - Color: {self.color_nombre}" if self.color_nombre else " (Galería / Ángulo)"
        return f"Imagen #{self.id} de {self.producto.nombre}{color_str}"


class Resena(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='resenas')
    nombre_cliente = models.CharField(max_length=100)
    comentario = models.TextField()
    calificacion = models.PositiveIntegerField(
        default=5,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Reseña'
        verbose_name_plural = 'Reseñas'
        ordering = ['-fecha']

    def __str__(self):
        return f"Reseña de {self.nombre_cliente} en {self.producto.nombre}"


class Orden(models.Model):
    ESTADOS = (
        ('PENDIENTE', 'Pendiente de Validación'),
        ('CONFIRMADO', 'Confirmado (Listo para Pagar)'),
        ('RECHAZADO', 'Rechazado'),
        ('PAGADO', 'Pago Recibido'),
        ('ENVIADO', 'Pedido Enviado'),
    )

    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    nombre_completo = models.CharField(max_length=150)
    email = models.EmailField()
    telefono = models.CharField(max_length=20)
    direccion = models.CharField(max_length=255)
    ciudad = models.CharField(max_length=100)

    costo_envio = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='PENDIENTE', db_index=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True, db_index=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Orden'
        verbose_name_plural = 'Órdenes'
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"Orden #{self.id} - {self.nombre_completo} ({self.estado})"


class ItemOrden(models.Model):
    orden = models.ForeignKey(Orden, on_delete=models.CASCADE, related_name='items')
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    talla = models.CharField(max_length=10)
    imagen_seleccionada = models.ForeignKey(ImagenProducto, on_delete=models.SET_NULL, null=True, blank=True)
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2)
    cantidad = models.PositiveIntegerField(default=1)

    class Meta:
        verbose_name = 'Ítem de Orden'
        verbose_name_plural = 'Ítems de Orden'

    @property
    def subtotal(self):
        return self.precio_unitario * self.cantidad

    def __str__(self):
        return f"{self.cantidad}x {self.producto.nombre} - Talla {self.talla}"
