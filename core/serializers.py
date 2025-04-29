from django.contrib.auth.models import User, Group
from rest_framework import serializers
from .models import (
    ActividadCliente, CarritoCompra, DetalleOrden, ImagenProducto, ItemCarrito, MetodoPago, Producto, Categoria, Marca, Etiqueta, Inventario,
    Envio, TipoEnvio, Orden, Estado, Cliente, Sucursal
)
from .utils import calcular_envio_para_orden
from django.core.exceptions import ValidationError
from drf_spectacular.utils import extend_schema_field

class ImagenProductoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImagenProducto
        fields = ['url_imagen']
        
class ProductoSerializer(serializers.ModelSerializer):
    popularidad = serializers.SerializerMethodField()
    imagenes = ImagenProductoSerializer(many=True, read_only=True)
    categoria_nombre = serializers.CharField(source='categoria.nombre', read_only=True)
    marca_nombre = serializers.CharField(source='marca.nombre', read_only=True)
    etiquetas_nombres = serializers.SerializerMethodField()
    class Meta:
        model = Producto
        fields = '__all__'
        
    @extend_schema_field(field=serializers.FloatField())
    def get_popularidad(self, obj):
        return obj.vendido_total + obj.visitas
    
    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_etiquetas_nombres(self, obj):
        return [etiqueta.nombre for etiqueta in obj.etiquetas.all()]
class ProductoListadoSerializer(serializers.ModelSerializer):
    imagenes = ImagenProductoSerializer(many=True, read_only=True)

    class Meta:
        model = Producto
        fields = ['id', 'nombre', 'precio', 'imagenes']
        
class MetodoPagoSerializer(serializers.ModelSerializer):
    class Meta:
        model = MetodoPago
        fields = '__all__'

class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = '__all__'


class MarcaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Marca
        fields = '__all__'


class EtiquetaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Etiqueta
        fields = '__all__'


class InventarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Inventario
        fields = '__all__'

class ItemCarritoSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)
    producto_precio = serializers.FloatField(source='producto.precio', read_only=True)
    class Meta:
        model = ItemCarrito
        fields = '__all__'

        read_only_fields = ('subtotal','carrito', 'fecha_agregado', 'fue_comprado')
    def update(self, instance, validated_data):
        validated_data.pop('producto', None)
        return super().update(instance, validated_data)
    
class CarritoCompraSerializer(serializers.ModelSerializer):
    class Meta:
        model = CarritoCompra
        fields = '__all__'

class SucursalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sucursal
        fields = '__all__'

class TipoEnvioSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoEnvio
        fields = '__all__'
        
class EnvioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Envio
        fields = '__all__'

class DetalleOrdenSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)

    class Meta:
        model = DetalleOrden
        fields = ['id', 'producto', 'producto_nombre', 'cantidad', 'precio_unitario', 'precio_total']

class OrdenSerializer(serializers.ModelSerializer):
    detalles = DetalleOrdenSerializer(many=True, read_only=True)
    estado = serializers.SerializerMethodField()
    
    tipo_envio = serializers.PrimaryKeyRelatedField(
        queryset=TipoEnvio.objects.all(), write_only=True
    )
    lat_cliente = serializers.FloatField(write_only=True, required=False)
    lon_cliente = serializers.FloatField(write_only=True, required=False)
    clasificacion_cliente = serializers.CharField(read_only=True)

    class Meta:
        model = Orden
        fields = [
            'id', 'direccion_entrega', 'total', 'sucursal', 'fecha',
            'tipo_envio', 'lat_cliente', 'lon_cliente', 'clasificacion_cliente', 
            'detalles', 'estado'
        ]
    @extend_schema_field(serializers.CharField())
    def get_estado(self, obj):
        if obj.pago:
            return obj.pago.estado
        return 'Pendiente'
    
    def create(self, validated_data):
        tipo_envio = validated_data.pop('tipo_envio')
        lat_cliente = validated_data.pop('lat_cliente', None)
        lon_cliente = validated_data.pop('lon_cliente', None)
        sucursal = validated_data['sucursal']

        if tipo_envio.costo_dinamico:
            if lat_cliente is None or lon_cliente is None:
                raise serializers.ValidationError("Ubicación del cliente requerida para este tipo de envío.")
            if not sucursal.latitud or not sucursal.longitud:
                raise serializers.ValidationError("La sucursal no tiene coordenadas definidas.")

        costo, tiempo_estimado = calcular_envio_para_orden(lat_cliente, lon_cliente, sucursal, tipo_envio)

        estado_inicial = Estado.objects.get(nombre__iexact="Procesando")

        envio = Envio.objects.create(
            tipo_envio=tipo_envio,
            costo=costo,
            tiempo_estimado=tiempo_estimado,
            lat_cliente=lat_cliente,
            lon_cliente=lon_cliente,
            estado=estado_inicial
        )

        usuario = self.context['request'].user
        cliente = Cliente.objects.get(usuario=usuario)

        orden = Orden.objects.create(
            cliente=cliente,
            direccion_entrega=validated_data['direccion_entrega'],
            sucursal=sucursal,
            envio=envio,
            total=0
        )

        return orden

class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']

class ClienteDetalleSerializer(serializers.ModelSerializer):
    usuario = UsuarioSerializer(read_only=True)
    nueva_contraseña = serializers.CharField(write_only=True, required=False, min_length=6)
    frecuencia_compra = serializers.IntegerField(read_only=True)
    preferencias = serializers.JSONField(required=False)
    class Meta:
        model = Cliente
        fields = ['telefono', 'direccion', 'usuario', 'nueva_contraseña', 'frecuencia_compra', 'preferencias']

    def update(self, instance, validated_data):
        usuario_data = validated_data.pop('usuario', {})
        nueva_contraseña = validated_data.pop('nueva_contraseña', None)
        usuario = instance.usuario

        for attr, value in usuario_data.items():
            setattr(usuario, attr, value)

        if nueva_contraseña:
            usuario.set_password(nueva_contraseña)
        usuario.save()

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        return instance
class RegistroClienteSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(write_only=True)
    last_name = serializers.CharField(write_only=True)
    email = serializers.EmailField(write_only=True)
    password = serializers.CharField(write_only=True, min_length=6)
    telefono = serializers.CharField(required=True)
    direccion = serializers.CharField(required=True)

    class Meta:
        model = Cliente
        fields = ['first_name', 'last_name', 'email', 'password', 'telefono', 'direccion']

    def validate_email(self, value):
        """ Verifica si el email ya está registrado """
        if User.objects.filter(email=value).exists():
            raise ValidationError("Este correo electrónico ya está registrado.")
        return value

    def create(self, validated_data):
        first_name = validated_data.pop('first_name')
        last_name = validated_data.pop('last_name')
        email = validated_data.pop('email')
        password = validated_data.pop('password')

        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )
        grupo_cliente, _ = Group.objects.get_or_create(name='cliente')
        user.groups.add(grupo_cliente)

        cliente = Cliente.objects.create(usuario=user, **validated_data)
        return cliente

class RegistroVendedorSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(write_only=True)
    last_name = serializers.CharField(write_only=True)
    email = serializers.EmailField(write_only=True)
    password = serializers.CharField(write_only=True, min_length=6)
    telefono = serializers.CharField(required=True)
    direccion = serializers.CharField(required=True)

    class Meta:
        model = Cliente
        fields = ['first_name', 'last_name', 'email', 'password', 'telefono', 'direccion']

    def validate_email(self, value):
        """ Verifica si el email ya está registrado """
        if User.objects.filter(email=value).exists():
            raise ValidationError("Este correo electrónico ya está registrado.")
        return value

    def create(self, validated_data):
        first_name = validated_data.pop('first_name')
        last_name = validated_data.pop('last_name')
        email = validated_data.pop('email')
        password = validated_data.pop('password')

        # Crear el usuario
        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )
        user.is_staff = True
        user.save()
        grupo_vendedor, _ = Group.objects.get_or_create(name='vendedor')
        grupo_cliente, _ = Group.objects.get_or_create(name='cliente')
        user.groups.add(grupo_vendedor, grupo_cliente)

        # Crear su perfil de cliente
        cliente = Cliente.objects.create(usuario=user, **validated_data)
        return cliente

    
class ActividadClienteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActividadCliente
        fields = ['cliente', 'producto', 'accion', 'descripcion', 'timestamp']
        read_only_fields = ['timestamp']

class ComandoVozSerializer(serializers.Serializer):
    texto = serializers.CharField()

class ProductoListadoSerializer(serializers.ModelSerializer):
    imagenes = ImagenProductoSerializer(many=True, read_only=True)
    marca_nombre = serializers.CharField(source='marca.nombre', read_only=True)
    etiquetas_nombres = serializers.SerializerMethodField()
    categoria_nombre = serializers.CharField(source='categoria.nombre', read_only=True)

    class Meta:
        model = Producto
        fields = ['id', 'nombre', 'precio', 'imagenes', 'marca_nombre', 'etiquetas_nombres', 'categoria_nombre']

    def get_etiquetas_nombres(self, obj):
        return [etiqueta.nombre for etiqueta in obj.etiquetas.all()]



class MarcaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Marca
        fields = ['id', 'nombre']

class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = ['id', 'nombre']

class CatalogoSerializer(serializers.Serializer):
    productos_destacados = ProductoListadoSerializer(many=True)
    recomendaciones = ProductoListadoSerializer(many=True)
    mas_vendidos = ProductoListadoSerializer(many=True)
    marcas_destacadas = MarcaSerializer(many=True)
    categorias_destacadas = CategoriaSerializer(many=True)