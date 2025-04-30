from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        try:
            import core.signals
            import core.signals_grupos
            import core.signals_envios
            import core.signals_datos_basicos
            import core.signals_clientes
            import core.signals_actividades
            
        except ImportError as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error cargando señales: {e}")
