from decimal import Decimal, InvalidOperation


def dollars_to_cents(text):
    try:
        amount = Decimal(text.strip())
    except InvalidOperation:
        return None
    if not amount.is_finite():
        return None
    if amount <= 0 or amount > 10000:
        return None
    if amount.as_tuple().exponent < -2:
        return None
    return int(amount * 100)


def cents_to_dollars(cents):
    return f"{cents // 100}.{cents % 100:02d}"


MAX_TOTAL_CENTS = 1_000_000  # 10000.00 USD, the same limit as before


def parse_quantity(text):
    """Whole number from 1 to 1000, or None."""
    text = text.strip()
    if not (text.isascii() and text.isdigit()):
        return None
    value = int(text)
    return value if 1 <= value <= 1000 else None
