# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import sys
import pprint
import socket

from werkzeug import urls

from odoo import _, api, models, http
from odoo.http import request
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_repr, float_compare

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment_epayco.controllers.main import EpaycoController

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _get_specific_rendering_values(self, processing_values):
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != 'epayco':
            return res

        api_url = EpaycoController._proccess_url
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
        epayco_values = {
            'api_url': api_url,
            "public_key": self.provider_id.epayco_public_key,
            "private_key": self.provider_id.epayco_private_key,
            "amount": str(float_repr(processing_values['amount'], self.currency_id.decimal_places or 2)),
            "tax": str(tax),
            'base_tax': str(base_tax),
            "currency": self.currency_id.name,
            "email": self.partner_email,
            "first_name": self.partner_name,
            "reference": str(plit_reference[0]),
            "lang_checkout": self.provider_id.epayco_checkout_lang,
            "checkout_external": external,
            "test": test,
            "response_url": urls.url_join(self.get_base_url(), EpaycoController._return_url),
            "confirmation_url": urls.url_join(self.get_base_url(), EpaycoController._confirm_url),
            "extra2": self.reference,
            "ip": ip_address
        }
        return epayco_values

    def _get_tx_from_notification_data(self, provider_code, notification_data):
        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        if provider_code != 'epayco' or len(tx) == 1:
            return tx

        reference = notification_data.get('x_extra2')
        sign = notification_data.get('x_signature')
        if not reference or not sign:
            raise ValidationError(
                "Epayco: " + _(
                    "Received data with missing reference (%(ref)s) or sign (%(sign)s).",
                    ref=reference, sign=sign
                )
            )

        tx = self.search([('reference', '=', reference), ('provider_code', '=', 'epayco')])
        if not tx:
            raise ValidationError(
                "Epayco: " + _("No transaction found matching reference %s.", reference)
            )

        # Verify signature
        sign_check = tx.provider_id._epayco_generate_sign(notification_data, incoming=True)
        if sign_check != sign:
            raise ValidationError(
                "Epayco: " + _(
                    "Invalid sign: received %(sign)s, computed %(check)s.",
                    sign=sign, check=sign_check
                )
            )

        return tx

    def _process_notification_data(self, notification_data):
        super()._process_notification_data(notification_data)
        if self.provider_code != 'epayco':
            return

        self.provider_reference = notification_data.get('x_extra2')
        signature = notification_data.get('x_signature')
        tx = self.search([('reference', '=', notification_data.get('x_extra2')), ('provider_code', '=', 'epayco')])
        shasign_check = tx.provider_id._epayco_generate_sign(notification_data, incoming=True)
        x_approval_code = notification_data.get('x_approval_code')
        x_cod_transaction_state = notification_data.get('x_cod_transaction_state')
        status = str(notification_data.get('x_transaction_state'))
        state_message = notification_data.get('x_response_reason_text')
        validation = False
        if float_compare(float(notification_data.get('x_amount', '0.0')), tx.amount, 2) == 0:
            if x_approval_code != "000000" and int(x_cod_transaction_state) == 1:
                validation = True
            else:
                if int(x_cod_transaction_state) != 1:
                    validation = True
                else:
                    validation = False

        if shasign_check == signature and validation == True:
            if int(x_cod_transaction_state) == 3:
                self._set_pending()
            if int(x_cod_transaction_state) == 1:
                self._set_done(state_message=state_message)
            if int(x_cod_transaction_state) in (2, 4, 6, 10, 11):
                self._set_canceled(state_message=state_message)
        else:
            _logger.warning(
                "invalid signature for transaction with reference %s",
                self.reference
            )
            self._set_error("Epayco: " + _("Invalid signature."))

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
