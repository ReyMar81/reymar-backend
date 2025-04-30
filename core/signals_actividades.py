import random
from django.db.models.signals import post_migrate
from django.dispatch import receiver
from .models import Producto, Cliente, ActividadCliente
from faker import Faker
from django.utils.timezone import now, timedelta

fake = Faker()

@receiver(post_migrate)
def simular_actividades_con_fechas_pasadas(sender, **kwargs):
    """Simula 1000 actividades de cliente con fechas aleatorias en el pasado."""
    clientes = Cliente.objects.all()
    productos = Producto.objects.all()

    if not clientes or not productos:
        print("⚠️ No hay clientes o productos en la base de datos.")
        return

    # Simulamos 1000 actividades de clientes
    for _ in range(1000):
        cliente = random.choice(clientes)
        producto = random.choice(productos)

        # Decidir si la acción será agregar al carrito o compra
        accion = random.choice(["agregar_carrito", "comprar"])

        # Generar una fecha aleatoria en el pasado (últimos 30 días)
        dias_anteriores = random.randint(1, 30)  # Aleatorio entre 1 y 30 días atrás
        fecha_pasada = now() - timedelta(days=dias_anteriores)

        # Crear actividad con acción aleatoria y fecha pasada
        ActividadCliente.objects.create(
            cliente=cliente,
            producto=producto,
            accion=accion,
            descripcion=f"Acción: {accion} en {fecha_pasada.strftime('%Y-%m-%d %H:%M:%S')}",
            timestamp=fecha_pasada
        )

    print("✅ 1000 actividades de cliente con fechas pasadas simuladas exitosamente.")
