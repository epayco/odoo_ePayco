# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import hashlib

import hashlib
import uuid
from werkzeug import urls

from odoo import api, fields, models, _
from odoo.addons.payment.models.payment_acquirer import ValidationError
from odoo.tools.float_utils import float_compare

import logging

_logger = logging.getLogger(__name__)


class PaymentAcquirerPayco(models.Model):
    _inherit = 'payment.acquirer'

    provider = fields.Selection(selection_add=[('payco', 'Payco')])
    payco_merchant_key = fields.Char(string='P_CUST_ID_CLIENTE', required_if_provider='payco', groups='base.group_user')
    payco_merchant_salt = fields.Char(string='PUBLIC_KEY', required_if_provider='payco', groups='base.group_user')
    payco_p_keyt = fields.Char(string='P_KEY', required_if_provider='payco', groups='base.group_user')
    payco_checkout_type = fields.Selection(
        selection=[('onpage', 'Onpage Checkout'),
                   ('standard', 'Standard Checkout')],
        required_if_provider='payco',
        string='Checkout Type',
        default='onpage')

    def _get_payco_urls(self, environment):
        """ Payco URLs"""
        self.ensure_one()
        base_url = self.get_base_url()
        return {'payco_form_url': urls.url_join(base_url,  '/payment/payco/checkout')}

    def _payco_generate_sign(self,  signature, values):
        """ Generate the signature for incoming communications.
        """
        p_cust_id_client = self.payco_merchant_key
        p_key = self.payco_p_keyt
        x_ref_payco = values.get('x_ref_payco')
        x_transaction_id = values.get('x_transaction_id')
        x_amount = values.get('x_amount')
        x_currency_code = values.get('x_currency_code')
        hash_str_bytes = bytes('%s^%s^%s^%s^%s^%s' % (
            p_cust_id_client,
            p_key,
            x_ref_payco,
            x_transaction_id,
            x_amount,
            x_currency_code), 'utf-8')
        hash_object = hashlib.sha256(hash_str_bytes)
        hash = hash_object.hexdigest()

        if hash == signature:
            shasign = True
        else:
            shasign = False

        return shasign

    @api.multi
    def payco_form_generate_values(self, values):
        self.ensure_one()
        base_url = self.get_base_url()
        partner_lang = values.get('partner') and values['partner'].lang
        env_test = 'false' if self.environment == 'prod' else 'true'
        lang = 'es' if 'es' in partner_lang else 'en'
        country = values.get('partner_country').code.lower()
        payco_checkout_external = (
            'false' if self.payco_checkout_type == 'onpage' else 'true')
        tx = self.env['payment.transaction'].search([('reference', '=', values.get('reference'))])
        if tx.state not in ['done', 'pending']:
            tx.reference = str(uuid.uuid4())
        url_confirmation = urls.url_join(base_url, '/payment/payco/confirmation/')
        url_response = urls.url_join(base_url, '/payment/payco/response/')
        payco_tx_values = dict(values)
        split_reference = payco_tx_values.get('reference').split('-')
        order = ''
        amount= 0.0
        tax = 0.0
        base_tax = 0.0
        if values['amount'] == values['partner'].last_website_so_id.amount_total:
            tax = values['partner'].last_website_so_id.amount_tax
            base_tax = values['partner'].last_website_so_id.amount_undiscounted
            amount = values['amount']
        if split_reference:
            order = split_reference[0]
        payco_tx_values.update({
            'public_key': self.payco_merchant_salt,
            'txnid': order,
            'amount': amount,
            'tax': tax,
            'base_tax': base_tax,
            'productinfo': tx.reference,
            'firstname': values.get('partner_name'),
            'email': values.get('partner_email'),
            'phone': values.get('partner_phone'),
            'currency_code': values['currency'] and values['currency'].name or '',
            'country_code': country,
            'epayco_checkout_external': payco_checkout_external,
            'epayco_env_test': env_test,
            'epayco_lang': lang,
            'response_url': url_response,
            'url_confirmation': url_confirmation,
            'extra1': order,
            'extra2': values['reference'],
            'extra3': "oDoo 12"
        })
        return payco_tx_values

    @api.multi
    def payco_get_form_action_url(self):
        self.ensure_one()
        return self._get_payco_urls(self.environment)['payco_form_url']


class PaymentTransactionPayco(models.Model):
    _inherit = 'payment.transaction'

    @api.model
    def _payco_form_get_tx_from_data(self, data):
        """ Given a data dict coming from Payco, verify it and find the related
        transaction record. """
        reference = data.get('x_extra1')
        pay_id = data.get('x_extra2')
        signature = data.get('x_signature')
        if not reference or not pay_id or not signature:
            raise ValidationError(_('Payco: received data with missing reference (%s) or pay_id (%s) or shashign (%s)') % (reference, pay_id, signature))

        transaction = self.search([('reference', '=', pay_id)])

        if not transaction:
            error_msg = (_('Payco: received data for reference %s; no order found') % (reference))
            raise ValidationError(error_msg)
        elif len(transaction) > 1:
            error_msg = (_('Payco: received data for reference %s; multiple orders found') % (reference))
            raise ValidationError(error_msg)

        #verify shasign
        shasign_check = transaction.acquirer_id._payco_generate_sign(signature, data)
        if shasign_check == False:
            raise ValidationError(_('Payco: invalid shasign, received %s, computed %s, for data %s') % (signature, shasign_check, data))
        return transaction

    @api.multi
    def _payco_form_get_invalid_parameters(self, data):
        invalid_parameters = []
        if self.acquirer_reference and data.get('x_transaction_id')  != self.acquirer_reference:
            invalid_parameters.append(
                ('Transaction Id', data.get('x_transaction_id'), self.acquirer_reference))
        #check what is buyed
        if int(self.acquirer_id.payco_merchant_key) != int(data.get('x_cust_id_cliente')):
            invalid_parameters.append(
                ('Custore_id', data.get('x_transaction_id'), self.acquirer_id.payco_merchant_key))

        if float_compare(float(data.get('x_amount', '0.0')), self.amount, 2) != 0:
            invalid_parameters.append(
                ('Amount', data.get('x_amount'), '%.2f' % self.amount))

        return invalid_parameters

    @api.multi
    def _payco_form_validate(self, data):
        cod_response = int(data.get('x_cod_response'))
        result = self.write({
            'acquirer_reference': data.get('x_ref_payco'),
            'date': fields.Datetime.now(),
        })
        if cod_response == 1:
            self._set_transaction_done()
        elif cod_response == 3:
            self._set_transaction_pending()
        else:
            self._set_transaction_cancel()
        return result
       