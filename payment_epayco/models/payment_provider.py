# Part of Odoo. See LICENSE file for full copyright and licensing details.

import hashlib

from odoo import api, fields, models

SUPPORTED_CURRENCIES = ('COP','USD')


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('epayco', 'Epayco')], ondelete={'epayco': 'set default'})
    epayco_cust_id = fields.Char(
        string="P_CUST_ID_CLIENTE",
        help="",
        required_if_provider='epayco',groups='base.group_system')
    epayco_public_key = fields.Char(
        string="PUBLIC_KEY",
        help="The ID solely used to identify the country-dependent shop with epayco",
        required_if_provider='epayco',groups='base.group_system')
    epayco_private_key = fields.Char(
        string="PRIVATE_KEY",
        help="The ID solely used to identify the country-dependent shop with epayco",
        required_if_provider='epayco', groups='base.group_system')
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
    def _get_compatible_providers(self, *args, currency_id=None, **kwargs):
        """ Override of payment to unlist Epayco acquirers for unsupported currencies. """
        providers = super()._get_compatible_providers(*args, currency_id=currency_id, **kwargs)

        currency = self.env['res.currency'].browse(currency_id).exists()
        if currency and currency.name not in SUPPORTED_CURRENCIES:
            providers = providers.filtered(lambda a: a.provider != 'epayco')

        return providers

    def _epayco_generate_sign(self, values, incoming=True):
        if incoming:
            p_key = self.epayco_p_key
            x_ref_payco = values.get('x_ref_payco')
            x_transaction_id = values.get('x_transaction_id')
            x_amount = values.get('x_amount')
            x_currency_code = values.get('x_currency_code')
            hash_str_bytes = bytes('%s^%s^%s^%s^%s^%s' % (
                self.epayco_cust_id,
                p_key,
                x_ref_payco,
                x_transaction_id,
                x_amount,
                x_currency_code), 'utf-8')
            hash_object = hashlib.sha256(hash_str_bytes)
            hash = hash_object.hexdigest()
        return hash