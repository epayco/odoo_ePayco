# Part of Odoo. See LICENSE file for full copyright and licensing details.

from hashlib import md5

from odoo import api, fields, models
from odoo.tools.float_utils import float_repr

SUPPORTED_CURRENCIES = ('COP','USD')


class PaymentAcquirerEpayco(models.Model):
    _inherit = 'payment.acquirer'

    provider = fields.Selection(
        selection_add=[('epayco', 'Epayco')], ondelete={'epayco': 'set default'})
    epayco_cust_id = fields.Char(
        string="P_CUST_ID_CLIENTE",
        help="",
        required_if_provider='epayco',groups='base.group_system')
    epayco_public_key = fields.Char(
        string="PUBLIC_KEY",
        help="The ID solely used to identify the country-dependent shop with epayco",
        required_if_provider='epayco',groups='base.group_system')
    epayco_p_key = fields.Char(
        string="P_KEY", required_if_provider='epayco',groups='base.group_system')
    epayco_checkout_type = fields.Selection(
        selection=[('onpage', 'Onpage Checkout'),
                   ('standard', 'Standard Checkout')],
        required_if_provider='epayco',
        string='Checkout Type',
        default='onpage')
    epayco_checkout_lang = fields.Selection(
        selection=[('en', 'English'),
                   ('es', 'Español')],
        required_if_provider='epayco',
        string='Checkout Type',
        default='es')

    @api.model
    def _get_compatible_acquirers(self, *args, currency_id=None, **kwargs):
        """ Override of payment to unlist Epayco acquirers for unsupported currencies. """
        acquirers = super()._get_compatible_acquirers(*args, currency_id=currency_id, **kwargs)

        currency = self.env['res.currency'].browse(currency_id).exists()
        if currency and currency.name not in SUPPORTED_CURRENCIES:
            acquirers = acquirers.filtered(lambda a: a.provider != 'epayco')

        return acquirers

    def _epayco_generate_sign(self, values, incoming=True):
        """ Generate the signature for incoming or outgoing communications.

        :param dict values: The values used to generate the signature
        :param bool incoming: Whether the signature must be generated for an incoming (Epayco to
                              Odoo) or outgoing (Odoo to Epayco) communication.
        :return: The signature
        :rtype: str
        """
        if incoming:
            data_string = '~'.join([
                self.epayco_cust_id,
                self.epayco_p_key,
                values['referenceCode'],
                # http://developers.epayco.com/en/web_checkout/integration.html
                # Section: 2. Response page > Signature validation
                # Epayco use the "Round half to even" rounding method
                # to generate their signature. This happens to be Python 3's
                # default rounding method.
                float_repr(float(values.get('TX_VALUE')), 1),
                values['currency'],
                values.get('transactionState'),
            ])
        else:
            data_string = '~'.join([
                self.epayco_cust_id,
                self.epayco_p_key,
                values['referenceCode'],
                float_repr(float(values['amount']), 1),
                values['currency'],
            ])
        return md5(data_string.encode('utf-8')).hexdigest()

    def _get_default_payment_method_id(self):
        self.ensure_one()
        if self.provider != 'epayco':
            return super()._get_default_payment_method_id()
        return self.env.ref('payment_epayco.payment_method_epayco').id