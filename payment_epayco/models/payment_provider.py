# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from hashlib import new as hashnew

import requests

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.payment_epayco import const


_logger = logging.getLogger(__name__)


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('epayco', "Epayco")], ondelete={'epayco': 'set default'})
    epayco_cust_id = fields.Char(
        string="P_CUST_ID_CLIENTE", help="",
        required_if_provider='epayco')
    epayco_public_key = fields.Char(
        string="PUBLIC_KEY",
        required_if_provider='epayco', groups='base.group_system')
    epayco_private_key = fields.Char(
        string="PRIVATE_KEY", required_if_provider='epayco', groups='base.group_system')
    epayco_p_key = fields.Char(
        string="P_KEY", required_if_provider='epayco', groups='base.group_system')
    epayco_checkout_type = fields.Selection(
        [('onpage', 'Onpage Checkout'), ('standard', 'Standard Checkout')],
        string="Checkout", required_if_provider='epayco',
    )
    epayco_checkout_lang = fields.Selection(
        [('en', 'English'), ('es', 'Español')],
        string="lenguage", required_if_provider='epayco',
    )

    #=== COMPUTE METHODS ===#

    def _compute_feature_support_fields(self):
        """ Override of `payment` to enable additional features. """
        super()._compute_feature_support_fields()
        self.filtered(lambda p: p.code == 'epayco').update({
            'support_tokenization': True,
        })

    #=== BUSINESS METHODS ===#

    def _get_supported_currencies(self):
        """ Override of `payment` to return the supported currencies. """
        supported_currencies = super()._get_supported_currencies()
        if self.code == 'epayco':
            supported_currencies = supported_currencies.filtered(
                lambda c: c.name in const.SUPPORTED_CURRENCIES
            )
        return supported_currencies

    @api.model
    def _get_compatible_providers(self, *args, is_validation=False, **kwargs):
        """ Override of payment to unlist epayco providers for validation operations. """
        providers = super()._get_compatible_providers(*args, is_validation=is_validation, **kwargs)

        if is_validation:
            providers = providers.filtered(lambda p: p.code != 'epayco')

        return providers


    def _epayco_generate_signature(self, values, incoming=True, format_keys=False):

        def _filter_key(_key):
            return not incoming or _key in const.VALID_KEYS

        key = self.epayco_shakey_out if incoming else self.epayco_shakey_in  # Swapped for epayco's POV
        if format_keys:
            formatted_items = [(k.upper().replace('_', '.'), v) for k, v in values.items()]
        else:
            formatted_items = [(k.upper(), v) for k, v in values.items()]
        sorted_items = sorted(formatted_items)
        signing_string = ''.join(f'{k}={v}{key}' for k, v in sorted_items if _filter_key(k) and v)
        shasign = hashnew(self.epayco_hash_function)
        shasign.update(signing_string.encode())
        return shasign.hexdigest()

    

    def _get_default_payment_method_codes(self):
        """ Override of `payment` to return the default payment method codes. """
        default_codes = super()._get_default_payment_method_codes()
        if self.code != 'epayco':
            return default_codes
        return const.DEFAULT_PAYMENT_METHODS_CODES
