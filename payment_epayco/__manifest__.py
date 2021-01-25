# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Epayco Payment Acquirer',
    'category': 'Accounting/Payment',
    'summary': 'Payment Acquirer: Epayco Implementation',
    'description': """
    Epayco Payment Acquirer for India.
    Epayco payment gateway supports only INR currency.
    """,
    'sequence': 365,
    'summary': 'Payment Acquirer: Epayco Implementation',
    'version': '1.0',
    'description': """Epayco Payment Acquirer""",
    'depends': ['payment'],
    'data': [
        'views/payment_views.xml',
        'views/payment_epayco_templates.xml',
        'data/payment_acquirer_data.xml',
    ],
    'post_init_hook': 'create_missing_journal_for_acquirers',
    'installable': True,
    'application': True,
    'post_init_hook': 'create_missing_journal_for_acquirers',
    'uninstall_hook': 'uninstall_hook',
}
