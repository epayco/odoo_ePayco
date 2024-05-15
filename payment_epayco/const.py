# Part of Odoo. See LICENSE file for full copyright and licensing details.

PAYMENT_STATUS_MAPPING = {
    'pending': ("3"),  # 46 = 3DS
    'done': ("1"),
    'cancel': ("2","4","9","10","11"),
    'declined': ("200",),
}

DEFAULT_PAYMENT_METHODS_CODES = [
    # Primary payment methods.
    'card',
    # Brand payment methods.
    'visa',
    'mastercard',
    'amex',
    'discover',
]

PAYMENT_METHODS_MAPPING = {
    'card': 'CreditCard',
    'paylib': 'Paylib',
    'p24': 'Przelewy24',
    'bancontact': 'BCMC',
    'paypal': 'PAYPAL',
    'ideal': 'IDEAL',
    'eps': 'EPS',
    'visa': 'VISA',
    'mastercard': 'MasterCard',
    'jcb': 'JCB',
    'klarna_paynow': 'KLARNA_PAYNOW',
    'klarna_pay_over_time': 'KLARNA_PAYLATER',
    'sofort': 'DirectEbanking',
}
