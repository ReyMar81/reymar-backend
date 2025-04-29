from django.db.models.signals import post_migrate
from django.dispatch import receiver
from .models import TipoEnvio

@receiver(post_migrate)
def crear_tipos_envio(sender, **kwargs):
    tipos_predefinidos = [
        {"nombre": "Moto", "descripcion": "Envío en moto", "velocidad_promedio": 50, "tarifa_km": 0.75},
        {"nombre": "Vehículo", "descripcion": "Envío en auto", "velocidad_promedio": 40, "tarifa_km": 1.00},
        {"nombre": "Camión", "descripcion": "Envío en camión", "velocidad_promedio": 30, "tarifa_km": 1.50},
        {"nombre": "Recoger en tienda", "descripcion": "Cliente recoge su pedido", "velocidad_promedio": 0, "tarifa_km": 0.00, "costo_dinamico": False},
    ]

    for tipo in tipos_predefinidos:
        TipoEnvio.objects.get_or_create(
            nombre=tipo["nombre"],
            defaults={
                "descripcion": tipo["descripcion"],
                "velocidad_promedio": tipo["velocidad_promedio"],
                "tarifa_km": tipo["tarifa_km"],
                "costo_dinamico": tipo.get("costo_dinamico", True)
            }
        )
print("✅ Tipos de envío creados correctamente.")