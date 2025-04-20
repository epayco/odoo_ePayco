# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Payment Provider: Epayco',
    'version': '18.0',
    'category': 'Accounting/Payment Providers',
    'sequence': 350,
    'summary': "ePayco",
    'description': " ",
    'depends': ['payment'],
    'data': [
        'views/payment_epayco_templates.xml',
        'views/payment_provider_views.xml',
        'data/payment_provider_data.xml',
    ],
      'images': ['static/description/main_screenshot.png'],
    #'assets': {
        #'web.assets_frontend': [
            #'payment_epayco/static/src/js/payment_form.js',
        #],
    #},
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    'license': 'LGPL-3',
}
