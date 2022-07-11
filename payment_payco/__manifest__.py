# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Payco Payment Acquirer',
    'version': '1.0',
    'category': 'Accounting/Payment Acquirers',
    'sequence': 100,
    'summary': 'Payment Acquirer: Payco Implementation',
    'description': """Payco Payment Acquirer""",
    'author': "Payco",
    'website': "http://paymob.com",
    'support': "support@warlocktechnologies.com",
    'depends': ['payment'],
    'data': [
        'views/payment_views.xml',
        'views/payment_payco_templates.xml',
        'data/payment_acquirer_data.xml',
    ],
    'images': ['static/images/screen_image.png'],
    'application': True,
    'uninstall_hook': 'uninstall_hook',
    'assets': {
        'web.assets_frontend': [
            'payment_payco/static/src/js/payment_form.js',
        ],
        'web.assets_backend': [
            'payment_payco/static/src/scss/backend.scss',
            'https://flashjs.paymob.com/v1/paymob.js',
            'payment_payco/static/src/js/paycowidget.js',
        ]
    },
    'license': 'LGPL-3',
}
