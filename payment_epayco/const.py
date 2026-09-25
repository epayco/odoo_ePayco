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

# SDK-1360: minimum age (in minutes) a `pending` epayco transaction must
# have before the reconciliation cron
# (`payment.transaction._cron_epayco_sync_pending_transactions`) will query
# epayco for its real status. Must be comfortably longer than a normal PSE
# round-trip (bank redirect + async confirmation webhook), so the cron
# never races a transaction that is still legitimately in progress.
EPAYCO_RECONCILE_MIN_AGE_MINUTES = 15

# SDK-1360: maximum age (in minutes) a `pending` epayco transaction can
# have before the reconciliation cron stops actively querying epayco for
# it (it is instead flagged for manual review, see
# `PaymentTransaction._epayco_flag_reconciliation_window_expired`).
# The cron itself runs every EPAYCO_RECONCILE_MIN_AGE_MINUTES (15 min, see
# data/ir_cron_data.xml), so a stuck transaction gets ~3 reconciliation
# attempts against epayco (at roughly the 15, 30 and 45 minute marks)
# before this 60-minute ceiling excludes it from further queries.
EPAYCO_RECONCILE_MAX_AGE_MINUTES = 60

# SDK-1360: max number of 'pending' transactions the reconciliation
# cron actively queries against epayco per run. Each one is a separate
# blocking HTTP GET (secure.epayco.co/validation/v1/reference/...), so
# an unbounded search could, during a spike (an outage on epayco's
# confirmation webhook, a flood of PSE checkouts, etc.), turn a single
# cron run into hundreds of sequential external calls -- holding the
# cron worker/DB transaction open far longer than a routine safety-net
# job should, and hammering epayco's API right when it may already be
# degraded. 50 per run, combined with the cron's own 15-minute cadence
# (see data/ir_cron_data.xml) and the `create_date asc` ordering below,
# throttles this naturally: whatever does not fit in one run's batch of
# 50 rolls over to the next run 15 minutes later, oldest-first, instead
# of starving. No explicit per-call sleep/backoff is added on top of
# this batching -- see PaymentTransaction._cron_epayco_sync_pending_transactions
# for why.
EPAYCO_RECONCILE_BATCH_SIZE = 50

# SDK-1360: ePayco tiene endpoints distintos para produccion y para
# develop/sandbox -- las credenciales de un ambiente no funcionan contra el
# otro (confirmado en vivo: las llaves de prueba compartidas de este
# ecosistema, usadas por los flujos ya validados de Shopify/Tiendanube, dan
# "Invalid client: client is invalid" contra los endpoints de produccion).
# Selecciona el par correcto segun el Test Mode del provider
# (`payment.provider.state == 'test'`) -- ver
# `PaymentProvider._epayco_get_login_url`/`_epayco_get_session_create_url`/
# `_epayco_get_validation_url` y `EpaycoController` (checkout_js_url).
EPAYCO_LOGIN_URL_PROD = 'https://apify.epayco.co/login'
EPAYCO_LOGIN_URL_TEST = 'https://eks-apify-service.epayco.io/login'

EPAYCO_SESSION_CREATE_URL_PROD = 'https://apify.epayco.co/payment/session/create'
EPAYCO_SESSION_CREATE_URL_TEST = 'https://eks-apify-service.epayco.io/payment/session/create'

EPAYCO_VALIDATION_URL_PROD = 'https://secure.epayco.co/validation/v1/reference/%s'
EPAYCO_VALIDATION_URL_TEST = 'https://eks-ms-checkout-transaction-service.epayco.io/validation/v1/reference/%s'

EPAYCO_CHECKOUT_JS_PROD = 'https://checkout.epayco.co/checkout-v2.js'
EPAYCO_CHECKOUT_JS_TEST = 'https://epayco-checkout-testing.s3.amazonaws.com/checkout.preprod-v2.js'
