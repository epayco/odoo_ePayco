# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import _, api, fields, models

from werkzeug import urls

from odoo.addons.payment_payco.const import SUPPORTED_CURRENCIES

_logger = logging.getLogger(__name__)


class PaymentAcquirer(models.Model):
    _inherit = 'payment.acquirer'

    provider = fields.Selection(
        selection_add=[('payco', "Payco")], ondelete={'payco': 'set default'})
    payco_cust_id = fields.Char(
        string="P_CUST_ID", help="P_CUST_ID",
        required_if_provider='payco')
    payco_public_key = fields.Char(
        string="PUBLICK_KEY", required_if_provider='payco', groups='base.group_system')
    payco_p_key = fields.Char(
        string="P_KEY", required_if_provider='payco', groups='base.group_system')
    payco_checkout_type = fields.Selection(
        selection=[('standard', 'Standard'),
                   ('onapegae', 'On page')],
        required_if_provider='payco',
        string='tipo de Checkout',
        default='standard')
        

    @api.model
    def _get_compatible_acquirers(self, *args, currency_id=None, **kwargs):
        """ Override of payment to unlist Payco acquirers when the currency is not supported. """
        acquirers = super()._get_compatible_acquirers(*args, currency_id=currency_id, **kwargs)

        currency = self.env['res.currency'].browse(currency_id).exists()
        if currency and currency.name not in SUPPORTED_CURRENCIES:
            acquirers = acquirers.filtered(lambda a: a.provider != 'payco')

        return acquirers

    def _payco_get_api_url(self):
        self.ensure_one()
        return ''

    def _get_default_payment_method_id(self):
        self.ensure_one()
        if self.provider != 'payco':
            return super()._get_default_payment_method_id()
        return self.env.ref('payment_payco.payment_method_payco').id

    def payco_form_generate_values(self, values):
        self.ensure_one()
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        values.update({
            "action_url": urls.url_join(base_url, '/payment/payco/transction/process')
        })
        return values