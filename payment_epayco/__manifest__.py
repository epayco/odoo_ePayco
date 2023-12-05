# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Payment Provider: Epayco',
    'version': '1.0',
    'category': 'Accounting/Payment Providers',
    'sequence': 100,
    'summary': 'Payment Provider: ePayco Implementation',
    'description': """ePayco Payment Provider""",
    'author': "ePayco",
    'website': "http://epayco.com",
    'depends': ['payment'],
    'data': [
        'views/payment_provider_views.xml',
        'views/payment_epayco_templates.xml',
        'data/payment_provider_data.xml',
    ],
    'images': ['static/images/screen_image.png'],
    'application': False,
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    'license': 'LGPL-3',
}
