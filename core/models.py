from django.utils import timezone
from django.db import models
from django.contrib.auth.models import User

class Categoria(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nombre
    
class Marca(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nombre
    
class Etiqueta(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nombre
    
class Sucursal(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    direccion = models.TextField()
    ciudad = models.CharField(max_length=100)

    latitud = models.FloatField(null=True, blank=True)
    longitud = models.FloatField(null=True, blank=True)
    def __str__(self):
        return self.nombre
    
class MetodoPago(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField()

    def __str__(self):
        return self.nombre
    
class Estado(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField()

    def __str__(self):
        return self.nombre
    
class TipoEnvio(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField()
    velocidad_promedio = models.FloatField(default=40) 
    costo_dinamico = models.BooleanField(default=True)
    tarifa_km = models.DecimalField(max_digits=5, decimal_places=2, default=1.0)
    def __str__(self):
        return self.nombre

class Producto(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField()
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    visitas = models.IntegerField(default=0)
    vendido_total = models.IntegerField(default=0)

    categoria = models.ForeignKey('Categoria', on_delete=models.PROTECT)
    marca = models.ForeignKey('Marca', on_delete=models.PROTECT)
    etiquetas = models.ManyToManyField('Etiqueta')

    def __str__(self):
        return self.nombre
    
class ImagenProducto(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='imagenes')
    url_imagen = models.URLField(max_length=200)

    def __str__(self):
        return f"Imagen de {self.producto.nombre}"

class Inventario(models.Model):
    stock = models.PositiveIntegerField()
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)

    producto = models.ForeignKey('Producto', on_delete=models.CASCADE)
    sucursal = models.ForeignKey('Sucursal', on_delete=models.CASCADE)
    def __str__(self):
        return f"{self.producto.nombre} en {self.sucursal.nombre}"

class Cliente(models.Model):
    telefono = models.CharField(max_length=20)
    direccion = models.TextField()
    fecha_registro = models.DateTimeField(default=timezone.now)
    preferencias = models.JSONField(null=True, blank=True)
    metodo_pago_preferido = models.ForeignKey('MetodoPago', null=True, blank=True, on_delete=models.SET_NULL)

    usuario = models.OneToOneField(User, on_delete=models.CASCADE)
    def __str__(self):
        return self.usuario.get_full_name() or self.usuario.username

class CarritoCompra(models.Model):
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    estado = models.CharField(max_length=20, default='Activo')
    total = models.DecimalField(max_digits=10, decimal_places=2, default= 0)
    
    cliente = models.ForeignKey('Cliente', on_delete=models.CASCADE)
    def __str__(self):
        return f"Carrito #{self.id} de {self.cliente}"


class ItemCarrito(models.Model):
    cantidad = models.PositiveIntegerField()
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, blank=True)
    fecha_agregado = models.DateTimeField(auto_now_add=True)

    carrito = models.ForeignKey('CarritoCompra', on_delete=models.CASCADE)
    producto = models.ForeignKey('Producto', on_delete=models.PROTECT)

    def save(self, *args, **kwargs):
        self.subtotal = self.cantidad * self.producto.precio
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.cantidad} x {self.producto.nombre} en Carrito #{self.carrito.id}"

class Envio(models.Model):
    tipo_envio = models.ForeignKey('TipoEnvio', on_delete=models.PROTECT)    
    estado = models.ForeignKey('Estado', on_delete=models.PROTECT, blank=True, null=True)

    costo = models.DecimalField(max_digits=10, decimal_places=2)
    tiempo_estimado = models.CharField(max_length=100)

    lat_cliente = models.FloatField(null=True, blank=True)
    lon_cliente = models.FloatField(null=True, blank=True)

    def __str__(self):
        return f"{self.tipo_envio.nombre} - {self.costo} Bs"

class Pago(models.Model):
    metodopago = models.ForeignKey('MetodoPago', on_delete=models.PROTECT)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    fecha = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=50, default="Exitoso")
    referencia_externa = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return f"{self.metodopago.nombre} - {self.monto}$"

class Orden(models.Model):
    fecha = models.DateTimeField(auto_now_add=True)
    direccion_entrega = models.TextField()
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    clasificacion_cliente = models.CharField(max_length=50, null=True, blank=True)

    pago = models.ForeignKey('Pago', on_delete=models.SET_NULL, null=True, blank=True)
    sucursal = models.ForeignKey('Sucursal', on_delete=models.PROTECT)
    envio = models.OneToOneField('Envio', on_delete=models.SET_NULL, null=True, blank=True)
    cliente = models.ForeignKey('Cliente', on_delete=models.PROTECT)

    def __str__(self):
        return f"Orden #{self.id} de {self.cliente}"

class DetalleOrden(models.Model):
    cantidad = models.PositiveIntegerField()
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    precio_total = models.DecimalField(max_digits=10, decimal_places=2, blank=True)
    
    producto = models.ForeignKey('Producto', on_delete=models.PROTECT)
    orden = models.ForeignKey('Orden', on_delete=models.CASCADE, related_name='detalles')

    def save(self, *args, **kwargs):
        if not self.precio_unitario:
            self.precio_unitario = self.producto.precio
        self.precio_total = self.cantidad * self.precio_unitario
        super().save(*args, **kwargs)
    def __str__(self):
        return f"{self.cantidad} x {self.producto.nombre} (Orden #{self.orden.id})"

class ActividadCliente(models.Model):
    cliente = models.ForeignKey('Cliente', on_delete=models.CASCADE)
    producto = models.ForeignKey('Producto', null=True, blank=True, on_delete=models.SET_NULL)
    accion = models.CharField(max_length=50) 
    descripcion = models.TextField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.cliente.usuario.username} hizo {self.accion} el {self.timestamp}"