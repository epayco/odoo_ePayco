# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import sys
import pprint

from werkzeug import urls

from odoo import _, api, models, http
from odoo.http import request
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_repr

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment_epayco.controllers.main import EpaycoController

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    @api.model
    def _compute_reference(self, provider, prefix=None, separator='-', **kwargs):
        if provider == 'epayco':
            if not prefix:
                prefix = self.sudo()._compute_reference_prefix(
                    provider, separator, **kwargs
                ) or None
            prefix = payment_utils.singularize_reference_prefix(prefix=prefix, separator=separator)
        return super()._compute_reference(provider, prefix=prefix, separator=separator, **kwargs)

    def _get_specific_rendering_values(self, processing_values):
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider != 'epayco':
            return res

        api_url = EpaycoController._proccess_url
        plit_reference = self.reference.split('-')
        sql = """select amount_tax from sale_order where name = '%s'
                """ % (plit_reference[0])
        http.request.cr.execute(sql)
        result = http.request.cr.fetchall() or []
        if result:
            (amount_tax) = result[0]
        for tax_amount in amount_tax:
            tax = tax_amount
        base_tax = float(float(float_repr(processing_values['amount'], self.currency_id.decimal_places or 2))-float(tax))
        external = 'true' if self.acquirer_id.epayco_checkout_type == 'standard' else 'false'
        epayco_values = {
            'api_url': api_url,
            "public_key": self.acquirer_id.epayco_public_key,
            "amount": str(float_repr(processing_values['amount'], self.currency_id.decimal_places or 2)),
            "tax": str(tax),
            'base_tax': str(base_tax),
            "currency": self.currency_id.name,
            "email": self.partner_email,
            "first_name": self.partner_name,
            "reference": str(plit_reference[0]),
            "lang": self.acquirer_id.epayco_checkout_lang,
            "checkout_external": external,
            "test": self.acquirer_id.state,
            "response_url": urls.url_join(self.get_base_url(), EpaycoController._return_url),
            "confirmation_url": urls.url_join(self.get_base_url(), EpaycoController._confirm_url),
            'extra2': self.reference
        }
        return epayco_values

    @api.model
    def _get_tx_from_feedback_data(self, provider, data):
        tx = super()._get_tx_from_feedback_data(provider, data)
        if provider != 'epayco':
            return tx

        reference = data.get('referenceCode')
        sign = data.get('signature')
        if not reference or not sign:
            raise ValidationError(
                "Epayco: " + _(
                    "Received data with missing reference (%(ref)s) or sign (%(sign)s).",
                    ref=reference, sign=sign
                )
            )

        tx = self.search([('reference', '=', reference), ('provider', '=', 'epayco')])
        if not tx:
            raise ValidationError(
                "Epayco: " + _("No transaction found matching reference %s.", reference)
            )

        # Verify signature
        sign_check = tx.acquirer_id._epayco_generate_sign(data, incoming=True)
        if sign_check != sign:
            raise ValidationError(
                "Epayco: " + _(
                    "Invalid sign: received %(sign)s, computed %(check)s.",
                    sign=sign, check=sign_check
                )
            )

        return tx

    def _process_feedback_data(self, data):
        super()._process_feedback_data(data)
        if self.provider != 'epayco':
            return

        self.acquirer_reference = data.get('transactionId')

        status = data.get('lapTransactionState')
        state_message = data.get('message')
        if status == 'PENDING':
            self._set_pending(state_message=state_message)
        elif status == 'APPROVED':
            self._set_done(state_message=state_message)
        elif status in ('EXPIRED', 'DECLINED'):
            self._set_canceled(state_message=state_message)
        else:
            _logger.warning(
                "received unrecognized payment state %s for transaction with reference %s",
                status, self.reference
            )
            self._set_error("Epayco: " + _("Invalid payment status."))