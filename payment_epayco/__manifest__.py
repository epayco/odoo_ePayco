# -*- coding: utf-8 -*-
# Copyright 2019 ePayco.co
# - Manuel Marquez <buzondemam@gmail.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    'name': 'Epayco Payment Acquirer',
    'summary': 'Epayco Payment Acquirer for the eCommerce.',
    'category': 'Accounting',
    'author': 'ePayco',
    "maintainers": ["mamcode"],
    'development_status': 'Production/Stable',
    'website': 'https://epayco.co/',
    'license': 'AGPL-3',
    'version': '12.0.1.0.0',
    'description': """Epayco Payment Acquirer""",
    'depends': ['payment', 'l10n_co', 'website_sale'],
    'data': [
        'security/ir.model.access.csv',
        'data/payment_icon.xml',
        'views/payment_epayco_templates.xml',
        'data/payment_acquirer.xml',
        'data/epayco_franchise.xml',
        'data/epayco_tx_state.xml',
        'data/epayco_document_type.xml',
        'views/payment_acquirer_views.xml',
        'views/payment_transaction_views.xml',
    ],
    'installable': True,
}
