# -*- coding: utf-8 -*-

{
    'name': 'Epayco Payment Acquirer',
    'category': 'Accounting/Payment',
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
    'installable': True,
    'application': True,
    'post_init_hook': 'create_missing_journal_for_acquirers',
    'uninstall_hook': 'uninstall_hook',
}
