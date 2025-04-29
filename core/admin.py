from django.contrib import admin
from .models import (
    Cliente, Categoria, Marca, Etiqueta, Sucursal, MetodoPago, Estado,
    TipoEnvio, Producto, Inventario, CarritoCompra, ItemCarrito,
    Orden, DetalleOrden, Envio, Pago
)

# Registro básico de modelos simples
admin.site.register(Categoria)
admin.site.register(Marca)
admin.site.register(Etiqueta)
admin.site.register(MetodoPago)
admin.site.register(Estado)
admin.site.register(TipoEnvio)
admin.site.register(Cliente)
admin.site.register(Envio)
admin.site.register(Pago)

@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'precio', 'visitas', 'vendido_total', 'popularidad')
    search_fields = ('nombre',)
    list_filter = ('marca', 'categoria')
    filter_horizontal = ('etiquetas',)
    readonly_fields = ('visitas', 'vendido_total', 'popularidad')

    def popularidad(self, obj):
        return obj.visitas + obj.vendido_total
    popularidad.short_description = 'Popularidad'

@admin.register(Inventario)
class InventarioAdmin(admin.ModelAdmin):
    list_display = ('producto', 'sucursal', 'stock', 'precio_unitario')
    list_filter = ('sucursal', 'producto')
    search_fields = ('producto__nombre', 'sucursal__nombre')

@admin.register(Sucursal)
class SucursalAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'direccion', 'ciudad')
    search_fields = ('nombre', 'ciudad')

@admin.register(CarritoCompra)
class CarritoCompraAdmin(admin.ModelAdmin):
    list_display = ('id', 'cliente', 'estado', 'fecha_creacion', 'total')
    list_filter = ('estado',)
    readonly_fields = ('total', 'fecha_creacion', 'fecha_actualizacion')

@admin.register(ItemCarrito)
class ItemCarritoAdmin(admin.ModelAdmin):
    list_display = ('carrito', 'producto', 'cantidad', 'subtotal')
    readonly_fields = ('subtotal',)
    list_filter = ('carrito', 'producto')

@admin.register(DetalleOrden)
class DetalleOrdenAdmin(admin.ModelAdmin):
    list_display = ('orden', 'producto', 'cantidad', 'precio_unitario', 'precio_total')
    search_fields = ('producto__nombre',)
    readonly_fields = ('precio_unitario', 'precio_total')

class DetalleOrdenInline(admin.TabularInline):
    model = DetalleOrden
    extra = 0
    readonly_fields = ('precio_unitario', 'precio_total')

@admin.register(Orden)
class OrdenAdmin(admin.ModelAdmin):
    list_display = ('id', 'cliente', 'fecha', 'total')
    list_filter = ('fecha',)
    search_fields = ('cliente__usuario__first_name', 'cliente__usuario__last_name')
    readonly_fields = ('total',)
    inlines = [DetalleOrdenInline]
