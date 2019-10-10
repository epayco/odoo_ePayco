# -*- coding: utf-8 -*-
# Copyright 2019 ePayco.co
# - Manuel Marquez <buzondemam@gmail.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _


class EpaycoTxState(models.Model):
    _name = 'epayco.tx.state'
    _rec_name = 'odoo_tx_state'

    @api.model
    def _get_odoo_tx_states(self):
        """Returns options for selection field odoo_tx_state."""
        payment_transaction = self.env['payment.transaction']
        model_fields = payment_transaction.fields_get(['state'])
        state_options_dict = dict(
            model_fields['state']['selection'])
        state_options = [(k, state_options_dict[k])
                         for k in state_options_dict]
        return state_options

    active = fields.Boolean(default=True)
    epayco_tx_code = fields.Integer(
        string='ePayco Code',
        help='Code of state of transaction comming from ePayco.')
    odoo_tx_state = fields.Selection(
        selection=_get_odoo_tx_states, string="Odoo Transaction State")
    payment_acquirer_id = fields.Many2one(
        comodel_name='payment.acquirer',
        string='Payment Acquirer',
        help='Only valid for ePayco.')

    _sql_constraints = [(
        'epayco_tx_code_unique',
        'unique(epayco_tx_code)',
        _('ePayco code already exists.'))]
