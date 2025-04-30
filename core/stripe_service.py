import stripe
from django.conf import settings
from .models import MetodoPago, Pago

stripe.api_key = settings.STRIPE_SECRET_KEY

def crear_payment_intent(orden):
    if not orden.pago:  # Si la orden no tiene un pago asociado
        monto_centavos = int(orden.total * 100)  # Stripe usa centavos
        try:
            payment_intent = stripe.PaymentIntent.create(
                amount=monto_centavos,
                currency='bob',  # Bolivianos
                description=f"Pago Orden #{orden.id}",
                metadata={'orden_id': orden.id},
                automatic_payment_methods={"enabled": True},
            )

            # Creamos un pago nuevo y asociamos el client_secret
            pago = Pago.objects.create(
                metodopago=MetodoPago.objects.get(nombre='Transferencia'),  # Método de pago
                monto=orden.total,
                estado="Pendiente",  # Estado inicial del pago
                referencia_externa=payment_intent.client_secret,  # Guardamos el client_secret aquí
            )

            # Asociamos el pago a la orden
            orden.pago = pago
            orden.save()

            return payment_intent.client_secret  # Retornamos el client_secret

        except stripe.error.StripeError as e:
            print(f"Error al crear el PaymentIntent: {e}")
            raise Exception("Error al procesar el pago con Stripe.")
    else:
        return orden.pago.referencia_externa  # Si ya existe un pago, usamos su referencia_externa


