# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'ePayco Payment Acquirer',
    'version': '1.0',
    'category': 'Accounting/Payment Acquirers',
    'sequence': 100,
    'summary': 'Payment Acquirer: ePayco Implementation',
    'description': """ePayco Payment Acquirer""",
    'author': "ePayco",
    'website': "http://epayco.com",
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
            'payment_payco/static/src/js/paycowidget.js',
        ]
    },
    'license': 'LGPL-3',
}
