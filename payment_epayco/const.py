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

EPAYCO_RECONCILE_MIN_AGE_MINUTES = 15

EPAYCO_RECONCILE_MAX_AGE_MINUTES = 60

EPAYCO_RECONCILE_BATCH_SIZE = 50

EPAYCO_LOGIN_URL_PROD = 'https://apify.epayco.co/login'
EPAYCO_LOGIN_URL_TEST = 'https://apify.epayco.co/login'

EPAYCO_SESSION_CREATE_URL_PROD = 'https://apify.epayco.co/payment/session/create'
EPAYCO_SESSION_CREATE_URL_TEST = 'https://apify.epayco.co/payment/session/create'

EPAYCO_VALIDATION_URL_PROD = 'https://secure.epayco.co/validation/v1/reference/%s'
EPAYCO_VALIDATION_URL_TEST = 'https://secure.epayco.co/validation/v1/reference/%s'

EPAYCO_CHECKOUT_JS_PROD = 'https://checkout.epayco.co/checkout-v2.js'
EPAYCO_CHECKOUT_JS_TEST = 'https://checkout.epayco.co/checkout-v2.js'
