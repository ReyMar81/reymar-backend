from django.db.models.signals import post_migrate
from django.contrib.auth.models import Group, Permission
from django.dispatch import receiver

@receiver(post_migrate)
def crear_grupos_y_permisos(sender, **kwargs):
    #--CLIENTE 
    cliente, _ = Group.objects.get_or_create(name='cliente')
    permisos_cliente = [
        'view_producto', 'view_categoria', 'view_marca', 'view_etiqueta',
        'view_metodopago', 'view_tipoenvio', 'view_carritocompra', 'add_carritocompra', 
        'change_carritocompra', 'view_itemcarrito', 'add_itemcarrito', 'change_itemcarrito',
        'delete_itemcarrito','add_orden', 'view_orden', 'delete_orden', 'delete_detalleorden',
        ]
    cliente.permissions.set(Permission.objects.filter(codename__in=permisos_cliente))

    #VENDEDOR
    vendedor, _ = Group.objects.get_or_create(name='vendedor')
    permisos_vendedor = [
        'view_producto', 'add_producto', 'change_producto',
        'view_categoria', 'view_marca', 'view_etiqueta',
        'view_inventario', 'add_inventario', 'change_inventario',
        'view_orden','view_cliente',
        ]
    vendedor.permissions.set(Permission.objects.filter(codename__in=permisos_vendedor))

    # ADMIN
    admin, _ = Group.objects.get_or_create(name='admin')
    admin.permissions.set(Permission.objects.all())

    print("✅ Grupos y permisos asignados correctamente.")
