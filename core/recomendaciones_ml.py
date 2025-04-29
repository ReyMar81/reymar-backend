from collections import Counter
from .models import ActividadCliente, Producto

from collections import Counter
from .models import ActividadCliente, Producto

def recomendar_productos_para(cliente_id, limite=6):
    actividades = ActividadCliente.objects.filter(
        cliente_id=cliente_id,
        accion__in=['ver', 'comprar']
    )
    if actividades.exists():
        # El cliente tiene historial: aprender de él
        productos_interesados = [actividad.producto for actividad in actividades if actividad.producto]
        categorias = Counter([p.categoria_id for p in productos_interesados if p.categoria_id])
        marcas = Counter([p.marca_id for p in productos_interesados if p.marca_id])
        categoria_preferida = categorias.most_common(1)[0][0] if categorias else None
        marca_preferida = marcas.most_common(1)[0][0] if marcas else None
        recomendaciones = Producto.objects.all()
        if categoria_preferida:
            recomendaciones = recomendaciones.filter(categoria_id=categoria_preferida)
        if marca_preferida:
            recomendaciones = recomendaciones.filter(marca_id=marca_preferida)
        # Excluir productos ya vistos o comprados
        productos_ids = [p.id for p in productos_interesados]
        recomendaciones = recomendaciones.exclude(id__in=productos_ids)
        # Ordenar también por popularidad
        recomendaciones = recomendaciones.order_by('-vendido_total', '-visitas')
        return recomendaciones.distinct()[:limite]
    else:
        # No hay historial: recomendar productos populares directamente
        productos_populares = Producto.objects.all().order_by('-vendido_total', '-visitas')[:limite]
        return productos_populares

def recomendar_productos_complementarios(producto_base, limite=6):
    etiquetas_producto = producto_base.etiquetas.all()
    # Buscar productos de la misma categoría
    productos_relacionados = Producto.objects.filter(
        categoria=producto_base.categoria
    ).exclude(id=producto_base.id)
    # Si el producto tiene etiquetas, filtrar también por etiquetas similares
    if etiquetas_producto.exists():
        productos_relacionados = productos_relacionados.filter(
            etiquetas__in=etiquetas_producto
        ).distinct()
    # Opcional: ordenar aleatorio para que no siempre sean los mismos
    productos_relacionados = productos_relacionados.order_by('?')
    return productos_relacionados[:limite]