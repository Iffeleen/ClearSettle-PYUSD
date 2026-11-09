import os

import braintree


def get_gateway():
    """Create a Braintree Sandbox gateway from environment variables."""
    return braintree.BraintreeGateway(
        braintree.Configuration(
            environment=braintree.Environment.Sandbox,
            merchant_id=os.getenv("BRAINTREE_MERCHANT_ID"),
            public_key=os.getenv("BRAINTREE_PUBLIC_KEY"),
            private_key=os.getenv("BRAINTREE_PRIVATE_KEY"),
        )
    )


def generate_client_token():
    """Return a client token the browser uses to show Braintree's card form."""
    return get_gateway().client_token.generate()


def create_sale(amount, nonce):
    """Charge `amount` (string like '12.50') using a payment nonce.
    Returns (details_dict, None) on success or (None, error_message)."""
    result = get_gateway().transaction.sale({
        "amount": amount,
        "payment_method_nonce": nonce,
        "options": {"submit_for_settlement": True},
    })
    if result.is_success:
        t = result.transaction
        return {
            "transaction_id": t.id,
            "status": t.status,
            "amount": str(t.amount),
        }, None
    return None, result.message
