# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'ePayco Payment Acquirer',
    'category': 'Payment Acquirer',
    'summary': 'Payment Acquirer: ePayco Implementation',
    'description': """ePayco payment gateway.""",
    'author': "ePayco",
    'website': "http://epayco.com",
    'depends': ['payment'],
    'data': [
        'views/payment_views.xml',
        'views/payment_epayco_templates.xml',
        'data/payment_acquirer_data.xml',
    ],
    'images': ['static/images/screen_image.png'],
    'post_init_hook': 'create_missing_journal_for_acquirers',
    'uninstall_hook': 'uninstall_hook',
    'license': 'LGPL-3',
}
