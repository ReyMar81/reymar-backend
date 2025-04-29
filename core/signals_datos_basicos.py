from django.db.models.signals import post_migrate
from django.dispatch import receiver
from .models import Estado, MetodoPago, Sucursal, Marca, Etiqueta, Categoria
from django.contrib.auth import get_user_model

@receiver(post_migrate)
def crear_datos_basicos(sender, **kwargs):
    MetodoPago.objects.get_or_create(nombre='Efectivo')
    MetodoPago.objects.get_or_create(nombre='QR')
    MetodoPago.objects.get_or_create(nombre='Transferencia')

    Sucursal.objects.get_or_create(nombre='Sucursal Central',ciudad='Santa cruz de la sierra', latitud=-17.78, longitud=-63.18)
    Sucursal.objects.get_or_create(nombre='Sucursal Norte',ciudad='Montero', latitud=-17.76, longitud=-63.15)

    Marca.objects.get_or_create(nombre='MarcaX')
    Marca.objects.get_or_create(nombre='ElectroPlus')

    Etiqueta.objects.get_or_create(nombre='Tecnología')
    Etiqueta.objects.get_or_create(nombre='Hogar')

    Categoria.objects.get_or_create(nombre='Audio')
    Categoria.objects.get_or_create(nombre='Accesorios')

    Estado.objects.get_or_create(nombre='Procesando', defaults={'descripcion': 'Orden en proceso de preparación'})
    Estado.objects.get_or_create(nombre='Enviado', defaults={'descripcion': 'Orden enviada al cliente'})
    Estado.objects.get_or_create(nombre='Entregado', defaults={'descripcion': 'Orden entregada exitosamente'})
    Estado.objects.get_or_create(nombre='Cancelado', defaults={'descripcion': 'Orden cancelada'})

    # ✅ Crear superusuario automáticamente
    User = get_user_model()
    if not User.objects.filter(username='reymar').exists():
        User.objects.create_superuser(username='reymar', email='reymar@example.com', password='reymar123')
        print("✅ Superusuario 'reymar' creado automáticamente.")
   
    print("✅ Datos básicos iniciales cargados.")