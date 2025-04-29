from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ActividadClienteAPIView, ActividadClienteAdminViewSet, CarritoView, CatalogoAPIView, ClienteAdminViewSet, ClienteOrdenesAdminViewSet, ComandoVozAPIView, CrearPagoStripeAPIView, DashboardAdminAPIView, ImagenProductoViewSet, ItemCarritoViewSet, MetodoPagoViewSet, OrdenAdminViewSet, ProductoViewSet, CategoriaViewSet, MarcaViewSet, 
    EtiquetaViewSet, InventarioViewSet, OrdenViewSet, 
    ConfirmarOrdenAPIView, ProductosBajoStockAPIView, ProductosComplementariosAPIView, RecomendacionesAvanzadasAPIView, RegistroClienteAPIView, RegistroVendedorAPIView, ReporteVentasAdminAPIView, StripeWebhookAPIView, SucursalViewSet, TipoEnvioViewSet, ClienteAPIView
)
router = DefaultRouter()
router.register(r'productos', ProductoViewSet, basename='producto')
router.register(r'metodospago', MetodoPagoViewSet, basename='metodopago')
router.register(r'categorias', CategoriaViewSet, basename='categoria')
router.register(r'marcas', MarcaViewSet, basename='marca')
router.register(r'etiquetas', EtiquetaViewSet, basename='etiqueta')
router.register(r'inventarios', InventarioViewSet, basename = 'inventario' )
router.register(r'ordenes', OrdenViewSet, basename='orden')
router.register(r'sucursales', SucursalViewSet, basename='sucursal')
router.register(r'items', ItemCarritoViewSet, basename='itemcarrito')
router.register(r'tipoEnvio', TipoEnvioViewSet, basename='TipoEnvio')
router.register(r'imagenes-producto', ImagenProductoViewSet, basename='imagenproducto')
router.register(r'admin/clientes', ClienteAdminViewSet, basename='admin-clientes')
router.register(r'admin/ordenes', OrdenAdminViewSet, basename='admin-ordenes')
router.register(r'admin/actividad-clientes', ActividadClienteAdminViewSet, basename='admin-actividad-clientes')

urlpatterns = [
    path('', include(router.urls)),
    path('carrito/', CarritoView.as_view(), name='carrito'),
    path('confirmar-orden/', ConfirmarOrdenAPIView.as_view(), name='confirmar-orden'),
    path('cliente/', ClienteAPIView.as_view(), name='cliente-detalle'),
    path('registro-cliente/', RegistroClienteAPIView.as_view(), name='registro-cliente'),
    path('registro-vendedor/', RegistroVendedorAPIView.as_view(), name='registro-vendedor'),
    path('actividad-cliente/', ActividadClienteAPIView.as_view(), name='actividad-cliente'),
    path('voz-comando/', ComandoVozAPIView.as_view(), name='voz-comando'),
    path('recomendaciones-avanzadas/', RecomendacionesAvanzadasAPIView.as_view(), name='recomendaciones-avanzadas'),
    path('crear-pago-stripe/', CrearPagoStripeAPIView.as_view(), name='crear-pago-stripe'),
    path('stripe-webhook/', StripeWebhookAPIView.as_view(), name='stripe-webhook'),
    path('catalogo/', CatalogoAPIView.as_view(), name='catalogo'),
    path('productos-complementarios/<int:producto_id>/', ProductosComplementariosAPIView.as_view(), name='productos_complementarios'),
    path('admin/dashboard/', DashboardAdminAPIView.as_view(), name='admin-dashboard'),
    path('admin/productos-bajo-stock/', ProductosBajoStockAPIView.as_view(), name='admin-productos-bajo-stock'),
    path('admin/clientes/<int:cliente_id>/ordenes/', ClienteOrdenesAdminViewSet.as_view({'get': 'list'}), name='admin-cliente-ordenes'),
    path('admin/reporte-ventas/', ReporteVentasAdminAPIView.as_view(), name='admin-reporte-ventas'),
]
