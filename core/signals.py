from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils.timezone import now
from decimal import Decimal
from .models import ItemCarrito, CarritoCompra, DetalleOrden, Inventario

# 🛒 Actualiza el total del carrito automáticamente
@receiver([post_save, post_delete], sender=ItemCarrito)
def actualizar_carrito(sender, instance, **kwargs):
    carrito = instance.carrito
    carrito.fecha_actualizacion = now()
    carrito.total = sum(item.subtotal for item in carrito.itemcarrito_set.all())
    carrito.save()

# 🧾 Actualiza el total de la orden con los productos y el costo de envío
@receiver([post_save, post_delete], sender=DetalleOrden)
def actualizar_total_orden(sender, instance, **kwargs):
    orden = instance.orden
    total_productos = sum(detalle.precio_total for detalle in orden.detalles.all())

    if orden.envio:
        envio_costo = orden.envio.costo
        if not isinstance(envio_costo, Decimal):
            envio_costo = Decimal(str(envio_costo))
        total = total_productos + envio_costo
    else:
        total = total_productos

    orden.total = total
    orden.save()

# 📦 Función para descontar stock - usar solo cuando el pago sea confirmado
def descontar_stock_orden(orden):
    for detalle in orden.detalles.all():
        producto = detalle.producto
        sucursal = orden.sucursal
        cantidad = detalle.cantidad

        try:
            inventario = Inventario.objects.select_for_update().get(producto=producto, sucursal=sucursal)
            if inventario.stock >= cantidad:
                inventario.stock -= cantidad
                inventario.save()
            else:
                print(f"❌ Stock insuficiente para producto: {producto.nombre}")
        except Inventario.DoesNotExist:
            print(f"❌ Inventario no encontrado para producto: {producto.nombre}")

# 🔄 Función para reponer stock si la orden se cancela o expira
def reponer_stock_orden(orden):
    for detalle in orden.detalles.all():
        producto = detalle.producto
        sucursal = orden.sucursal
        cantidad = detalle.cantidad

        try:
            inventario = Inventario.objects.select_for_update().get(producto=producto, sucursal=sucursal)
            inventario.stock += cantidad
            inventario.save()
        except Inventario.DoesNotExist:
            print(f"❌ Inventario no encontrado para producto: {producto.nombre}")