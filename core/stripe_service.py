import stripe
from django.conf import settings

stripe.api_key = settings.STRIPE_SECRET_KEY

def crear_payment_intent(monto_bolivianos, descripcion, orden_id):
    monto_centavos = int(monto_bolivianos * 100)  # Stripe trabaja en centavos

    payment_intent = stripe.PaymentIntent.create(
        amount=monto_centavos,
        currency='bob',  # Bolivianos
        description=descripcion,
        metadata={'orden_id': orden_id},
        automatic_payment_methods={"enabled": True}
    )

    return payment_intent
