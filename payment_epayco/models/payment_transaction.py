# -*- coding: utf-8 -*-
# Copyright 2019 ePayco.co
# - Manuel Marquez <buzondemam@gmail.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import hashlib
import logging

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    epayco_txid = fields.Char('ePayco Transaction ID')
    epayco_franchise_id = fields.Many2one(
        comodel_name='epayco.franchise',
        string='ePayco Franchise')

    @api.multi
    def get_tx_signature(self, data):
        """Build hash sha256 for signature of payment transaction."""
        self.ensure_one()
        p_cust_id_cliente = self.acquirer_id.epayco_p_cust_id
        p_key = self.acquirer_id.epayco_p_key
        x_ref_payco = data.get('x_ref_payco')
        x_transaction_id = data.get('x_transaction_id')
        x_amount = data.get('x_amount')
        x_currency_code = data.get('x_currency_code')
        hash_str_bytes = bytes('%s^%s^%s^%s^%s^%s' % (
            p_cust_id_cliente,
            p_key,
            x_ref_payco,
            x_transaction_id,
            x_amount,
            x_currency_code), 'utf-8')
        hash_object = hashlib.sha256(hash_str_bytes)
        hash = hash_object.hexdigest()
        return hash

    @api.model
    def _epayco_form_get_tx_from_data(self, data):
        """ Given a data dict coming from ePayco, verify it and
        find the related transaction record. """
        tx_signature = data.get('x_signature')
        tx_reference = data.get('x_id_invoice')
        if not tx_reference or not tx_signature:
            error_msg = 'ePayco: received data with missing reference' \
                ' (%s) or signature (%s)' % (tx_reference, tx_signature)
            _logger.info(error_msg)

        tx = self.search([('reference', '=', tx_reference)])

        if not tx or len(tx) > 1:
            error_msg = 'ePayco: received data for reference %s' % (
                tx_reference)
            if not tx:
                error_msg += '; no order found'
            else:
                error_msg += '; multiple order found'
            _logger.info(error_msg)
            raise ValidationError(error_msg)

        signature_received = data.get('x_signature')
        signature_computed = tx.get_tx_signature(data)
        if signature_received != signature_computed:
            error_msg = (
                'ePayco: invalid signature, received %s, computed %s, '
                'for data %s' % (signature_received, signature_computed, data)
            )
            _logger.info(error_msg)
            raise ValidationError(error_msg)
        return tx

    @api.multi
    def _epayco_form_get_invalid_parameters(self, data):
        """Find invalid parameters comming from data of ePayco."""
        invalid_parameters = []
        if ((self.acquirer_reference and data.get('x_transaction_id'))
                != self.acquirer_reference):
            invalid_parameters.append(
                ('Transaction Id', data.get('x_transaction_id'),
                 self.acquirer_reference))

        if int(self.acquirer_id.epayco_p_cust_id) != data.get(
                'x_cust_id_cliente'):
            invalid_parameters.append((
                'Customer ID',
                data.get('x_cust_id_cliente'),
                self.acquirer_id.epayco_p_cust_id))
        return invalid_parameters

    @api.model
    def _get_epayco_tx_state(self, x_cod_transaction_state):
        """Get and return the corresponding state for odoo transaction
        mapping from states of ePayco transaction."""
        epayco_tx_state = self.env['epayco.tx.state']
        tx_state = epayco_tx_state.search([
            ('epayco_tx_code', '=', x_cod_transaction_state)])
        if not tx_state:
            raise ValidationError(_(
                'no odoo transaction status has been associated with '
                "epayco's state code %s.") % x_cod_transaction_state)
        return tx_state.odoo_tx_state

    def _epayco_form_validate(self, data):
        """Validate data comming from ePayco response and
        update odoo transaction."""
        state = self._get_epayco_tx_state(data.get('x_cod_transaction_state'))
        vals = {
            'epayco_txid': data.get('x_transaction_id'),
            'acquirer_reference': data.get('x_transaction_id'),
        }

        epayco_franchise = self.env['epayco.franchise']
        franchise = epayco_franchise.search([(
            'code', '=', data.get('x_franchise'))])
        if franchise:
            vals['epayco_franchise_id'] = franchise.id

        state_message = ""
        if state == 'done':
            vals['state_message'] = _('Ok: %s') % data.get(
                'x_transaction_state')
            self._set_transaction_done()
        elif state == 'pending':
            state_message = _('State: %s (%s)')
            self._set_transaction_pending()
        elif state == 'cancel':
            state_message = _('State: %s (%s)')
            self._set_transaction_cancel()
        else:
            state_message = _('Error: feedback error %s (%s)')
        if state_message:
            vals['state_message'] = state_message % (
                data.get('x_transaction_state'),
                data.get('x_response_reason_text'),
            )
            if state == 'error':
                _logger.warning(vals['state_message'])
                self._set_transaction_error(vals['state_message'])
        self.write(vals)
        return state != 'error'
