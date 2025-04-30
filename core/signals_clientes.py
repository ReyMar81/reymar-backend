from django.db.models.signals import post_migrate
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import Cliente
from faker import Faker
import random

User = get_user_model()
fake = Faker()

@receiver(post_migrate)
@receiver(post_migrate)
def crear_clientes(sender, **kwargs):
    """Crear 100 clientes de manera automática tras la migración, verificando si el usuario ya existe."""
    for _ in range(100):
        first_name = fake.first_name()
        last_name = fake.last_name()
        email = f"{first_name.lower()}.{last_name.lower()}@gmail.com"
        password = f"{first_name.lower()}123"  # Contraseña con el nombre
        telefono = f"7{random.randint(10000000, 99999999)}"  # Número aleatorio
        direccion = fake.address().replace("\n", ", ")  # Dirección realista

        # Verifica si el usuario ya existe antes de crear
        if User.objects.filter(username=email).exists():
            print(f"⚠️ El usuario con email {email} ya existe. Se omitirá.")
            continue  # Si el usuario existe, salta a la siguiente iteración

        # Crear el usuario
        user = User.objects.create_user(username=email, email=email, password=password, first_name=first_name, last_name=last_name)

        # Crear el cliente asociado al usuario
        Cliente.objects.create(usuario=user, telefono=telefono, direccion=direccion)

    print("✅ 100 clientes creados automáticamente.")

