# Part of Odoo. See LICENSE file for full copyright and licensing details.

PAYMENT_STATUS_MAPPING = {
    'pending': ("3"),  # 46 = 3DS
    'done': ("1"),
    'canceled': ("2","4","9","10","11"),
    'declined': ("200",),
    'error': ('rejected',),
}

SUPPORTED_CURRENCIES = [
    'USD',
    'COP'
]

DEFAULT_PAYMENT_METHODS_CODES = [
    # Primary payment methods.
    'epayco',
    'card',
    # Brand payment methods.
    'visa',
    'mastercard',
    'amex',
    'discover',
]

PAYMENT_METHODS_MAPPING = {
    'epayco': 'ePayco',
    'card': 'debit_card,credit_card,prepaid_card',
    'paypal': 'PAYPAL',
    'visa': 'VISA',
    'mastercard': 'MasterCard',
}
