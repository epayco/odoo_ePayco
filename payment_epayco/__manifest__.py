# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'ePayco Payment Acquirer',
    'category': 'Accounting/Payment Acquirers',
    'sequence': 101,
    'summary': 'Payment Acquirer: ePayco Implementation',
    'description': """ePayco payment gateway.""",
    'depends': ['payment'],
    'data': [
        'views/payment_views.xml',
        'views/payment_epayco_templates.xml',
        'data/payment_acquirer_data.xml',
    ],
    'application': True,
    'post_init_hook': 'create_missing_journal_for_acquirers',
    'uninstall_hook': 'uninstall_hook',
    'license': 'LGPL-3',
}
