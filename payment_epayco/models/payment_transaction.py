# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint
import uuid
import socket

from lxml import etree, objectify
from werkzeug import urls

from odoo import _, api, models, http
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_repr, float_compare
from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment_epayco import const
from odoo.addons.payment_epayco.controllers.main import EpaycoController


_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    @api.model
    def _compute_reference(self, provider_code, prefix=None, separator='-', **kwargs):
        if provider_code != 'epayco':
            return super()._compute_reference(provider_code, prefix=prefix, **kwargs)

        if not prefix:
            prefix = self.sudo()._compute_reference_prefix(provider_code, separator, **kwargs) or None
        prefix = payment_utils.singularize_reference_prefix(prefix=prefix, max_length=40)
        return super()._compute_reference(provider_code, prefix=prefix, **kwargs)

    def _get_specific_processing_values(self, processing_values):
        res = super()._get_specific_processing_values(processing_values)
        if self.provider_code != 'epayco':
            return res

        if self.operation in ('online_token', 'offline'):
            return {}

        return self._get_specific_rendering_values(self)

    def _get_specific_rendering_values(self, processing_values):
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != 'epayco':
            return res
        plit_reference = self.reference.split('-')
        tax = 0
        is_tax = self.get_tax('sale_order', plit_reference[0])
        if is_tax:
            tax = is_tax
        else:
            is_tax = self.get_tax('account_move', plit_reference[0])
            if is_tax:
                tax = is_tax

        hostname = socket.gethostname()
        ip_address = socket.gethostbyname(hostname)
        base_tax = float(
            float(float_repr(processing_values['amount'], self.currency_id.decimal_places or 2)) - float(tax))
        external = 'true' if self.provider_id.epayco_checkout_type == 'standard' else 'false'
        test = 'true' if self.provider_id.state == 'test' else 'false'
        return_url = urls.url_join(self.provider_id.get_base_url(), EpaycoController._return_url)
        confirm_url = urls.url_join(self.provider_id.get_base_url(), EpaycoController._confirm_url)
        api_url = urls.url_join(self.provider_id.get_base_url(), EpaycoController._proccess_url)
        language = self.partner_lang[0:2]
        rendering_values = {
            "public_key": self.provider_id.epayco_public_key,
            "private_key": self.provider_id.epayco_private_key,
            "amount": str(float_repr(processing_values['amount'], self.currency_id.decimal_places or 2)),
            "tax": str(tax),
            "base_tax": str(base_tax),
            "currency": self.currency_id.name,
            "email": self.partner_email or '',
            "first_name": self.partner_name or '',
            "reference": str(plit_reference[0]),
            "lang_checkout": self.provider_id.epayco_checkout_lang,
            "checkout_external": external,
            "test": test,
            "response_url": return_url,
            "confirmation_url": confirm_url,
            "extra2": self.reference,
            "ip": ip_address,
            'address': self.partner_address or '',
            'zip': self.partner_zip or '',
            'city': self.partner_city or '',
            'country': self.partner_country_id.code or '',
            'cellphone': self.partner_phone or '',
            'total': payment_utils.to_minor_currency_units(self.amount, None, 2),
            'language': language,
            'url': return_url
        }
        rendering_values.update({
            'api_url': api_url,
        })
        return rendering_values

    def _get_tx_from_notification_data(self, provider_code, notification_data):
        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        if provider_code != 'epayco' or len(tx) == 1:
            return tx

        reference = notification_data.get('x_extra2')
        tx = self.search([('reference', '=', reference), ('provider_code', '=', 'epayco')])
        if not tx:
            raise ValidationError(
                "epayco: " + _("No transaction found matching reference %s.", reference)
            )
        return tx

    def _process_notification_data(self, notification_data):
        super()._process_notification_data(notification_data)
        # Update the payment state.
        payment_status = notification_data.get('x_cod_response')
        if payment_status in const.PAYMENT_STATUS_MAPPING['pending']:
            self._set_pending()
        elif payment_status in const.PAYMENT_STATUS_MAPPING['done']:
            self._set_done()
        elif payment_status in const.PAYMENT_STATUS_MAPPING['cancel']:
            self._set_canceled()
        else:  # Classify unknown payment statuses as `error` tx state
            _logger.info(
                "received data with invalid payment status (%s) for transaction with reference %s",
                payment_status, self.reference
            )
            self._set_error(
                "epayco: " + _("Received data with invalid payment status: %s", payment_status)
            )

    def _epayco_tokenize_from_notification_data(self, notification_data):
        token = self.env['payment.token'].create({
            'provider_id': self.provider_id.id,
            'payment_method_id': self.payment_method_id.id,
            'payment_details': notification_data.get('CARDNO')[-4:],  # epayco pads details with X's.
            'partner_id': self.partner_id.id,
            'provider_ref': notification_data['ALIAS'],
        })
        self.write({
            'token_id': token.id,
            'tokenize': False,
        })
        _logger.info(
            "created token with id %(token_id)s for partner with id %(partner_id)s from "
            "transaction with reference %(ref)s",
            {
                'token_id': token.id,
                'partner_id': self.partner_id.id,
                'ref': self.reference,
            },
        )

    def get_tax(self, table, name):
        sql = """select amount_tax from %s where name = '%s'
                        """ % (table, name)
        http.request.cr.execute(sql)
        result = http.request.cr.fetchall() or []
        amount_tax = 0
        tax = 0
        if result:
            (amount_tax) = result[0]
            if len(amount_tax) > 0:
                for tax_amount in amount_tax:
                    tax = tax_amount
        return tax
