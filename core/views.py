from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample, OpenApiResponse, extend_schema_view
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, serializers, viewsets
from django.db import transaction
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import DjangoModelPermissions, AllowAny, IsAuthenticated, IsAuthenticatedOrReadOnly, IsAdminUser
from decimal import Decimal
from django.utils.timezone import now

import stripe
from core.signals import descontar_stock_orden
from django.conf import settings
from core.stripe_service import crear_payment_intent
from core.recomendaciones_ml import recomendar_productos_complementarios, recomendar_productos_para
from .models import (ActividadCliente, ImagenProducto, ItemCarrito, MetodoPago, 
    Pago, Producto, Categoria, Marca, Etiqueta, Inventario, Orden, CarritoCompra,
    TipoEnvio, Cliente, Estado, Envio, DetalleOrden, 
    Sucursal
)
from .serializers import (
    ActividadClienteSerializer, CatalogoSerializer, ComandoVozSerializer, 
    ImagenProductoSerializer, ItemCarritoSerializer, MetodoPagoSerializer, ProductoListadoSerializer, 
    ProductoSerializer, CategoriaSerializer, MarcaSerializer, EtiquetaSerializer, 
    InventarioSerializer, OrdenSerializer, RegistroClienteSerializer, RegistroVendedorSerializer, 
    SucursalSerializer, TipoEnvioSerializer, ClienteDetalleSerializer
)
from .utils import calcular_envio_para_orden

class ProductoViewSet(viewsets.ModelViewSet):
    queryset = Producto.objects.all()

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [DjangoModelPermissions()]

    def get_serializer_class(self):
        if self.action == 'list':
            return ProductoListadoSerializer 
        return ProductoSerializer

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()

        if request.user.is_authenticated:
            try:
                cliente = Cliente.objects.get(usuario=request.user)
                ActividadCliente.objects.create(
                    cliente=cliente,
                    producto=instance,
                    accion='ver'
                )
                instance.visitas += 1
                instance.save()
            except Cliente.DoesNotExist:
                pass

        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
class ImagenProductoViewSet(viewsets.ModelViewSet):
    queryset = ImagenProducto.objects.all()
    serializer_class = ImagenProductoSerializer
    
class MetodoPagoViewSet(viewsets.ModelViewSet):
    queryset = MetodoPago.objects.all()
    serializer_class = MetodoPagoSerializer
    permission_classes = [DjangoModelPermissions]

class CategoriaViewSet(viewsets.ModelViewSet):
    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [DjangoModelPermissions()]

class MarcaViewSet(viewsets.ModelViewSet):
    queryset = Marca.objects.all()
    serializer_class = MarcaSerializer
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [DjangoModelPermissions()]

class EtiquetaViewSet(viewsets.ModelViewSet):
    queryset = Etiqueta.objects.all()
    serializer_class = EtiquetaSerializer
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [DjangoModelPermissions()]

class InventarioViewSet(viewsets.ModelViewSet):
    queryset = Inventario.objects.all()
    serializer_class = InventarioSerializer
    permission_classes = [DjangoModelPermissions]

class ItemCarritoViewSet(viewsets.ModelViewSet):
    queryset = ItemCarrito.objects.all()
    serializer_class = ItemCarritoSerializer
    permission_classes = [DjangoModelPermissions]

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]
        return [DjangoModelPermissions()]

    def get_queryset(self):
        cliente = Cliente.objects.get(usuario=self.request.user)
        return ItemCarrito.objects.filter(carrito__cliente=cliente, carrito__estado='Activo')

    def perform_create(self, serializer):
        cliente = Cliente.objects.get(usuario=self.request.user)
        carrito, _ = CarritoCompra.objects.get_or_create(cliente=cliente, estado='Activo')
        item =serializer.save(carrito=carrito)

        ActividadCliente.objects.create(
        cliente=cliente,
        producto=item.producto,
        accion="agregar_carrito"
    )
    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return super().update(request, *args, **kwargs)

class SucursalViewSet(viewsets.ModelViewSet):
    queryset = Sucursal.objects.all()
    serializer_class = SucursalSerializer
    permission_classes = [DjangoModelPermissions]

class TipoEnvioViewSet(viewsets.ModelViewSet):
    queryset = TipoEnvio.objects.all()
    serializer_class = TipoEnvioSerializer
    permission_classes = [DjangoModelPermissions]

class OrdenViewSet(viewsets.ModelViewSet):
    queryset = Orden.objects.all()
    serializer_class = OrdenSerializer
    permission_classes = [DjangoModelPermissions]

    def get_queryset(self):
        cliente = Cliente.objects.get(usuario=self.request.user)
        return Orden.objects.filter(cliente=cliente)


@extend_schema(
    parameters=[
        OpenApiParameter(name='tipo_envio', description='ID del tipo de envío', required=False, type=int),
        OpenApiParameter(name='sucursal', description='ID de la sucursal', required=False, type=int),
        OpenApiParameter(name='lat_cliente', description='Latitud del cliente', required=False, type=float),
        OpenApiParameter(name='lon_cliente', description='Longitud del cliente', required=False, type=float),
    ]
)
@extend_schema(
    responses=ActividadClienteSerializer(many=True)
)
class CarritoView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            cliente = Cliente.objects.get(usuario=request.user)
            carrito = CarritoCompra.objects.filter(cliente=cliente, estado="Activo").first()

            if not carrito:
                return Response({"error": "No hay carrito activo."}, status=400)
            ActividadCliente.objects.create(
                cliente=cliente,
                accion="ver_carrito"
            )

            items = carrito.itemcarrito_set.all()
            subtotal = sum(item.subtotal for item in items)

            tipo_envio_id = request.query_params.get("tipo_envio")
            sucursal_id = request.query_params.get("sucursal")
            lat_cliente = request.query_params.get("lat_cliente")
            lon_cliente = request.query_params.get("lon_cliente")

            costo_envio = 0
            tiempo_estimado = None

            if tipo_envio_id and sucursal_id:
                try:
                    tipo_envio = TipoEnvio.objects.get(id=tipo_envio_id)
                    sucursal = Sucursal.objects.get(id=sucursal_id)

                    if tipo_envio.costo_dinamico:
                        if not lat_cliente or not lon_cliente:
                            return Response({"error": "Faltan coordenadas del cliente."}, status=400)

                        costo_envio, tiempo_estimado = calcular_envio_para_orden(
                            float(lat_cliente), float(lon_cliente), sucursal, tipo_envio
                        )
                    else:
                        costo_envio, tiempo_estimado = calcular_envio_para_orden(
                            0, 0, sucursal, tipo_envio
                        )

                except (TipoEnvio.DoesNotExist, Sucursal.DoesNotExist):
                    return Response({"error": "Tipo de envío o sucursal inválida."}, status=400)

            total = float(subtotal) + float(costo_envio)

            return Response({
                "items": ItemCarritoSerializer(items, many=True).data,
                "subtotal": subtotal,
                "costo_envio": costo_envio,
                "tiempo_estimado": tiempo_estimado,
                "total": total
            })

        except Exception as e:
            import traceback
            print("Error interno en carrito:", traceback.format_exc())
            return Response({"error": "Error interno", "detalle": str(e)}, status=500)

@extend_schema(
    request={
        "application/json": {
            "example": {
                "tipo_envio": 1,
                "lat_cliente": -17.7851,
                "lon_cliente": -63.1819,
                "direccion_entrega": "Calle Las Palmas #123",
                "sucursal": 1
            }
        }
    },
    responses={
        201: {
            "description": "Orden creada exitosamente",
            "content": {
                "application/json": {
                    "example": {
                        "mensaje": "Orden creada exitosamente.",
                        "orden_id": 5
                    }
                }
            }
        },
        400: {
            "description": "Error en la solicitud",
            "content": {
                "application/json": {
                    "example": {
                        "error": "Faltan datos obligatorios."
                    }
                }
            }
        }
    }
)
class ConfirmarOrdenAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        cliente = Cliente.objects.get(usuario=request.user)
        carrito = CarritoCompra.objects.filter(cliente=cliente, estado="Activo").first()

        if not carrito or not carrito.itemcarrito_set.exists():
            return Response({"error": "El carrito está vacío."}, status=status.HTTP_400_BAD_REQUEST)

        tipo_envio_id = request.data.get("tipo_envio")
        lat_cliente = request.data.get("lat_cliente")
        lon_cliente = request.data.get("lon_cliente")
        direccion_entrega = request.data.get("direccion_entrega")
        sucursal_id = request.data.get("sucursal")

        if not all([tipo_envio_id, sucursal_id, direccion_entrega]):
            return Response({"error": "Faltan datos obligatorios."}, status=status.HTTP_400_BAD_REQUEST)

        tipo_envio = TipoEnvio.objects.get(id=tipo_envio_id)
        sucursal = Sucursal.objects.get(id=sucursal_id)

        costo_envio, tiempo_estimado = calcular_envio_para_orden(
            lat_cliente, lon_cliente, sucursal, tipo_envio
        )

        estado = Estado.objects.get(nombre__iexact="Procesando")

        envio = Envio.objects.create(
            tipo_envio=tipo_envio,
            costo=costo_envio,
            tiempo_estimado=tiempo_estimado,
            lat_cliente=Decimal(str(lat_cliente)),
            lon_cliente=Decimal(str(lon_cliente)),
            estado=estado
        )

        orden = Orden.objects.create(
            cliente=cliente,
            direccion_entrega=direccion_entrega,
            sucursal=sucursal,
            envio=envio,
            total=Decimal('0.00')
        )

        for item in carrito.itemcarrito_set.all():
            DetalleOrden.objects.create(
                orden=orden,
                producto=item.producto,
                cantidad=item.cantidad,
                precio_unitario=item.producto.precio
            )
            
            ActividadCliente.objects.create(
                cliente=cliente,
                producto=item.producto,
                accion="comprar"
            )
        carrito.estado = "Procesado"
        carrito.save()

        return Response({
            "mensaje": "Orden creada exitosamente.",
            "orden_id": orden.id
        }, status=status.HTTP_201_CREATED)

@extend_schema_view(
    get=extend_schema(
        responses=ClienteDetalleSerializer
    ),
    put=extend_schema(
        request=ClienteDetalleSerializer,
        responses=ClienteDetalleSerializer
    )
)
class ClienteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            cliente = Cliente.objects.get(usuario=request.user)
            serializer = ClienteDetalleSerializer(cliente)
            return Response(serializer.data)
        except Cliente.DoesNotExist:
            return Response({'error': 'No existe perfil de cliente para este usuario.'}, status=404)

    def put(self, request):
        cliente = Cliente.objects.get(usuario=request.user)
        serializer = ClienteDetalleSerializer(cliente, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)

@extend_schema(
    request=RegistroClienteSerializer,
    responses={
        201: OpenApiResponse(
            description="Cliente creado con éxito",
            examples=[
                OpenApiExample(
                    name="Registro exitoso",
                    value={
                        "mensaje": "Cliente registrado correctamente.",
                        "refresh": "jwt-refresh...",
                        "access": "jwt-access..."
                    }
                )
            ]
        )
    }
)
class RegistroClienteAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegistroClienteSerializer(data=request.data)
        if serializer.is_valid():
            cliente = serializer.save()
            user = cliente.usuario
            refresh = RefreshToken.for_user(user)

            return Response({
                "mensaje": "Cliente registrado correctamente.",
                "refresh": str(refresh),
                "access": str(refresh.access_token)
            }, status=201)
        return Response(serializer.errors, status=400)
@extend_schema(
    request=RegistroVendedorSerializer,
    responses={
        201: OpenApiResponse(
            description="Vendedor creado con éxito",
            examples=[
                OpenApiExample(
                    name="Registro vendedor",
                    value={
                        "mensaje": "Vendedor registrado correctamente."
                    }
                )
            ]
        )
    }
)
class RegistroVendedorAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = RegistroVendedorSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"mensaje": "Vendedor registrado correctamente."}, status=201)
        return Response(serializer.errors, status=400)

@extend_schema(
    request=ActividadClienteSerializer, 
    responses=ActividadClienteSerializer
)
class ActividadClienteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ActividadClienteSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"mensaje": "Actividad registrada"}, status=201)
        return Response(serializer.errors, status=400)

    def get(self, request):
        cliente = Cliente.objects.get(usuario=request.user)
        actividades = ActividadCliente.objects.filter(cliente=cliente).order_by('-timestamp')
        serializer = ActividadClienteSerializer(actividades, many=True)
        return Response(serializer.data)

@extend_schema(
    request=ComandoVozSerializer,
    responses=ProductoSerializer(many=True)
)    
class ComandoVozAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ComandoVozSerializer(data=request.data)
        if serializer.is_valid():
            texto = serializer.validated_data['texto'].lower()
            productos = Producto.objects.filter(nombre__icontains=texto)
            resultado = ProductoSerializer(productos, many=True)

            cliente = Cliente.objects.get(usuario=request.user)
            ActividadCliente.objects.create(
                cliente=cliente,
                accion="voz_busqueda",
                descripcion=texto
            )

            return Response({
                "resultado": resultado.data,
                "mensaje": f"{productos.count()} producto(s) encontrados para '{texto}'"
            })
        return Response(serializer.errors, status=400)

@extend_schema(
    responses=ProductoSerializer(many=True)
)
class RecomendacionesAvanzadasAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cliente = request.user.cliente
        limite_total = 10
        historial_ids = ActividadCliente.objects.filter(
            cliente=cliente,
            accion__in=['ver', 'comprar']
        ).values_list('producto_id', flat=True)
        historial_productos = Producto.objects.filter(id__in=historial_ids).distinct()
        productos_vistos = historial_productos.exclude(id__isnull=True)
        recomendaciones = list(productos_vistos)[:limite_total]
        if len(recomendaciones) < limite_total:
            productos_extra = recomendar_productos_para(cliente.id, limite=limite_total)
            productos_existentes_ids = [p.id for p in recomendaciones]

            productos_faltantes = [
                p for p in productos_extra
                if p.id not in productos_existentes_ids
            ]

            recomendaciones += productos_faltantes[:(limite_total - len(recomendaciones))]

        serializer = ProductoSerializer(recomendaciones, many=True)
        return Response(serializer.data)

class CrearPagoStripeRequestSerializer(serializers.Serializer):
    orden_id = serializers.IntegerField()
@extend_schema(
    request=CrearPagoStripeRequestSerializer,
    responses={200: None}
)

class CrearPagoStripeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        orden_id = request.data.get('orden_id')

        if not orden_id:
            return Response({"error": "orden_id es obligatorio."}, status=400)

        try:
            orden = Orden.objects.get(id=orden_id, cliente__usuario=request.user)
        except Orden.DoesNotExist:
            return Response({"error": "Orden no encontrada."}, status=404)

        payment_intent = crear_payment_intent(
            monto_bolivianos=float(orden.total),
            descripcion=f"Pago Orden #{orden.id}",
            orden_id=orden.id
        )

        return Response({
            "client_secret": payment_intent.client_secret
        })

@extend_schema(
    request=None,
    responses=None
)
class StripeWebhookAPIView(APIView):
    authentication_classes = []
    permission_classes = [] 

    def post(self, request):
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
        endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, endpoint_secret
            )
        except ValueError as e:
            # Invalid payload
            print("⚠️ Payload inválido")
            return Response(status=400)
        except stripe.error.SignatureVerificationError as e:
            # Invalid signature
            print("⚠️ Firma inválida")
            return Response(status=400)

        if event['type'] == 'payment_intent.succeeded':
            payment_intent = event['data']['object']

            orden_id = payment_intent['metadata'].get('orden_id')
            if not orden_id:
                print("⚠️ orden_id no encontrado en metadata")
                return Response(status=400)

            try:
                orden = Orden.objects.get(id=orden_id)
            except Orden.DoesNotExist:
                print(f"❌ Orden ID {orden_id} no encontrada")
                return Response(status=404)

            metodopago, _ = MetodoPago.objects.get_or_create(
                nombre="Stripe",
                defaults={"descripcion": "Pago realizado mediante Stripe"}
            )

            pago = Pago.objects.create(
                metodopago=metodopago,
                monto=orden.total,
                estado="Exitoso",
                referencia_externa=payment_intent['id']
            )
            orden.pago = pago
            orden.estado = "Pagada"
            orden.save()
            descontar_stock_orden(orden)

            print(f"✅ Orden {orden_id} marcada como pagada y stock descontado.")

        return Response(status=200)
    
@extend_schema(
    responses=CatalogoSerializer
)
class CatalogoAPIView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request):
        cliente = None
        if request.user.is_authenticated:
            cliente = getattr(request.user, 'cliente', None)

        productos_destacados = Producto.objects.all().order_by('-id')[:10]
        productos_mas_vendidos = Producto.objects.all().order_by('-vendido_total', '-visitas')[:10]
        marcas_destacadas = Marca.objects.all()[:6]
        categorias_destacadas = Categoria.objects.all()[:6]

        recomendaciones = []
        limite_total = 10

        if cliente:
            historial_ids = ActividadCliente.objects.filter(
                cliente=cliente,
                accion__in=['ver', 'comprar']
            ).values_list('producto_id', flat=True)

            historial_productos = Producto.objects.filter(id__in=historial_ids).distinct()
            productos_vistos = historial_productos.exclude(id__isnull=True)

            if productos_vistos.exists():
                recomendaciones = list(productos_vistos)[:limite_total]
                if len(recomendaciones) < limite_total:
                    productos_extra = recomendar_productos_para(cliente.id, limite=limite_total)
                    productos_existentes_ids = [p.id for p in recomendaciones]
                    productos_faltantes = [
                        p for p in productos_extra
                        if p.id not in productos_existentes_ids
                    ]
                    recomendaciones += productos_faltantes[:(limite_total - len(recomendaciones))]
            else:
                # Cliente logueado pero sin historial: recomendar populares
                recomendaciones = recomendar_productos_para(cliente.id, limite=limite_total)
        else:
            # Usuario no logueado: recomendar productos populares directamente
            recomendaciones = Producto.objects.all().order_by('-vendido_total', '-visitas')[:limite_total]

        return Response({
            'productos_destacados': ProductoListadoSerializer(productos_destacados, many=True).data,
            'recomendaciones': ProductoListadoSerializer(recomendaciones, many=True).data,
            'mas_vendidos': ProductoListadoSerializer(productos_mas_vendidos, many=True).data,
            'marcas_destacadas': MarcaSerializer(marcas_destacadas, many=True).data,
            'categorias_destacadas': CategoriaSerializer(categorias_destacadas, many=True).data,
        })

@extend_schema(
    responses=ProductoListadoSerializer(many=True)
)
class ProductosComplementariosAPIView(APIView):
    def get(self, request, producto_id):
        try:
            producto = Producto.objects.get(id=producto_id)
        except Producto.DoesNotExist:
            return Response({'error': 'Producto no encontrado.'}, status=404)

        complementarios = recomendar_productos_complementarios(producto)

        serializer = ProductoListadoSerializer(complementarios, many=True)
        return Response(serializer.data)
    
@extend_schema_view(
    list=extend_schema(summary="Listar todos los clientes"),
    retrieve=extend_schema(summary="Ver detalle de un cliente")
)
class ClienteAdminViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Cliente.objects.all()
    serializer_class = ClienteDetalleSerializer
    permission_classes = [IsAdminUser]

@extend_schema_view(
    list=extend_schema(
        summary="Listar órdenes de un cliente",
        description="Devuelve todas las órdenes hechas por un cliente, usando su ID en la ruta."
    )
)
class ClienteOrdenesAdminViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = OrdenSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        cliente_id = self.kwargs['cliente_id']
        return Orden.objects.filter(cliente_id=cliente_id)

@extend_schema_view(
    list=extend_schema(summary="Listar todas las órdenes"),
    retrieve=extend_schema(summary="Detalle de orden"),
    partial_update=extend_schema(summary="Actualizar estado de una orden")
)
class OrdenAdminViewSet(viewsets.ModelViewSet):
    queryset = Orden.objects.all()
    serializer_class = OrdenSerializer
    permission_classes = [IsAdminUser]

    def partial_update(self, request, *args, **kwargs):

        return super().partial_update(request, *args, **kwargs)

@extend_schema_view(
    list=extend_schema(summary="Listar todas las actividades de los clientes")
)
class ActividadClienteAdminViewSet(viewsets.ReadOnlyModelViewSet):

    queryset = ActividadCliente.objects.all().order_by('-timestamp')
    serializer_class = ActividadClienteSerializer
    permission_classes = [IsAdminUser]

@extend_schema(
    summary="Ver resumen de ventas, clientes y pedidos",
    responses={
        200: OpenApiResponse(description="Resumen con totales y productos destacados")
    }
)
class DashboardAdminAPIView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        hoy = now().date()

        total_clientes = Cliente.objects.count()
        total_ordenes = Orden.objects.count()
        total_ventas = sum(orden.total for orden in Orden.objects.all())
        ordenes_hoy = Orden.objects.filter(fecha__date=hoy).count()
        productos_top = Producto.objects.order_by('-vendido_total')[:5]

        return Response({
            "total_clientes": total_clientes,
            "total_ordenes": total_ordenes,
            "total_ventas": total_ventas,
            "ordenes_hoy": ordenes_hoy,
            "top_productos": [{"nombre": p.nombre, "vendidos": p.vendido_total} for p in productos_top]
        })

@extend_schema(
    summary="Listar productos con stock bajo",
    responses={
        200: InventarioSerializer(many=True)
    }
)
class ProductosBajoStockAPIView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        bajo_stock = Inventario.objects.filter(stock__lt=5)
        serializer = InventarioSerializer(bajo_stock, many=True)
        return Response(serializer.data)
    
@extend_schema(
    summary="Informe de ventas por fecha",
    parameters=[
        OpenApiParameter(name='fecha_desde', type=str, description='Fecha desde (YYYY-MM-DD)', required=False),
        OpenApiParameter(name='fecha_hasta', type=str, description='Fecha hasta (YYYY-MM-DD)', required=False),
    ],
    responses={
        200: OrdenSerializer(many=True),
        400: OpenApiResponse(description="Error de formato de fecha")
    }
)
class ReporteVentasAdminAPIView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        fecha_desde = request.query_params.get('fecha_desde')
        fecha_hasta = request.query_params.get('fecha_hasta')

        ordenes = Orden.objects.all().order_by('-fecha')

        if fecha_desde:
            ordenes = ordenes.filter(fecha__date__gte=fecha_desde)
        if fecha_hasta:
            ordenes = ordenes.filter(fecha__date__lte=fecha_hasta)

        serializer = OrdenSerializer(ordenes, many=True)
        return Response(serializer.data)
