import math
from decimal import Decimal, ROUND_HALF_UP

def calcular_distancia_km(lat1, lon1, lat2, lon2):
    """
    Calcula la distancia entre dos puntos (lat/lon) usando la fórmula de Haversine.
    Devuelve la distancia en kilómetros (Decimal).
    """
    # Forzamos a float solo para los cálculos trigonométricos
    lat1 = float(lat1)
    lon1 = float(lon1)
    lat2 = float(lat2)
    lon2 = float(lon2)

    R = 6371  # Radio de la Tierra en kilómetros
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    distancia = R * c

    # Convertimos a Decimal (2 decimales redondeados)
    return Decimal(distancia).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def calcular_envio_para_orden(lat_cliente, lon_cliente, sucursal, tipo_envio):
    """
    Calcula el costo y el tiempo estimado de un envío, basado en la distancia y el tipo de envío.
    Retorna una tupla: (Decimal costo, str tiempo_estimado).
    """
    if tipo_envio.costo_dinamico:
        distancia = calcular_distancia_km(
            lat_cliente, lon_cliente,
            sucursal.latitud, sucursal.longitud
        )

        tarifa_km = tipo_envio.tarifa_km
        velocidad = tipo_envio.velocidad_promedio

        costo = (distancia * tarifa_km).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        if velocidad == 0:
            tiempo = "A coordinar"
        else:
            minutos = int((float(distancia) / float(velocidad)) * 60)
            tiempo = f"{minutos} minutos" if minutos < 60 else f"{minutos // 60}h {minutos % 60}min"
        return costo, tiempo

    return Decimal('0.00'), "A coordinar en tienda"

