# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import hashlib

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
    
    def _epayco_generate_signature(self, values, incoming=True):
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

    @api.model
    def _get_compatible_providers(self, *args, is_validation=False, **kwargs):
        """ Override of payment to unlist epayco providers for validation operations. """
        providers = super()._get_compatible_providers(*args, is_validation=is_validation, **kwargs)

        if is_validation:
            providers = providers.filtered(lambda p: p.code != 'epayco')

        return providers

    def _get_supported_currencies(self):
        """ Override of `payment` to return the supported currencies. """
        supported_currencies = super()._get_supported_currencies()
        if self.code == 'epayco':
            supported_currencies = supported_currencies.filtered(
                lambda c: c.name in const.SUPPORTED_CURRENCIES
            )
        return supported_currencies

    def _get_default_payment_method_codes(self):
        """ Override of `payment` to return the default payment method codes. """
        default_codes = super()._get_default_payment_method_codes()
        if self.code != 'epayco':
            return default_codes
        return const.DEFAULT_PAYMENT_METHODS_CODES

    def get_epayco_token(self):
        """
        Obtiene el token JWT de ePayco usando las credenciales configuradas en el proveedor.
        Retorna el token como string, o None si falla.
        """
        url = "https://apify.epayco.co/login"
        public_key = self.epayco_public_key
        private_key = self.epayco_private_key
        headers = {'Content-Type': 'application/json'}
        try:
            resp = requests.post(
                url,
                headers=headers,
                json={},
                auth=requests.auth.HTTPBasicAuth(public_key, private_key),
                timeout=15
            )
        except requests.RequestException as e:
            _logger.error(f"Error en la llamada a ePayco API: {e}")
            return None
        if resp.status_code != 200:
            _logger.error(f"Respuesta no OK: {resp.status_code} - {resp.text}")
            return None
        data = resp.json()
        return data.get('token')
