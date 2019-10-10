# -*- coding: utf-8 -*-
# Copyright 2019 ePayco.co
# - Manuel Marquez <buzondemam@gmail.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models, _


class EpaycoFranchise(models.Model):
    _name = 'epayco.franchise'

    code = fields.Char()
    name = fields.Char()
    active = fields.Boolean(default=True)
    payment_acquirer_id = fields.Many2one(
        comodel_name='payment.acquirer',
        string='Payment Acquirer',
        help='Only valid for ePayco.')

    _sql_constraints = [(
        'code_unique',
        'unique(code)',
        _('Code already exists for a franchise.'))]
