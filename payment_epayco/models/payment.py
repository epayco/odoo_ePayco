# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from builtins import print
import hashlib

import hashlib
from re import S
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

    def _get_payco_urls(self):
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

    def payco_form_generate_values(self, values):
        self.ensure_one()
        base_url = self.get_base_url()
        partner_lang = values.get('partner') and values['partner'].lang
        test = 'false' if self.state == 'enabled' else 'true'
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
        tax = values['partner'].last_website_so_id.amount_tax
        base_tax = values['partner'].last_website_so_id.amount_undiscounted
        amount = values['partner'].last_website_so_id.amount_total
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
            'epayco_env_test': test,
            'epayco_lang': lang,
            'response_url': url_response,
            'url_confirmation': url_confirmation,
            'extra1': order,
            'extra2': values['reference'],
            'extra3': test
        })
        return payco_tx_values

    def payco_get_form_action_url(self):
        self.ensure_one()
        return self._get_payco_urls()['payco_form_url']


class PaymentTransactionPayco(models.Model):
    _inherit = 'payment.transaction'

    @api.model
    def _payco_form_get_tx_from_data(self, data):
        """ Given a data dict coming from ePayco, verify it and find the related
        transaction record. """
        reference = data.get('x_extra1')
        pay_id = data.get('x_extra2')
        signature = data.get('x_signature')

        if not reference or not pay_id or not signature:
            raise ValidationError(_('ePayco: received data with missing reference (%s) or pay_id (%s) or shashign (%s)') % (reference, pay_id, signature))

        transaction = self.search([('reference', '=', pay_id)])
        if not transaction:
            error_msg = (_('Payco: received data for reference %s; no order found') % (reference))
            raise ValidationError(error_msg)
        elif len(transaction) > 1:
            error_msg = (_('Payco: received data for reference %s; multiple orders found') % (reference))
            raise ValidationError(error_msg)

        return transaction

    def _payco_form_get_invalid_parameters(self, data):
        invalid_parameters = []
        #check what is buyed
        if int(self.acquirer_id.payco_merchant_key) != int(data.get('x_cust_id_cliente')):
            invalid_parameters.append(
                ('Custore_id', data.get('x_cust_id_cliente'), self.acquirer_id.payco_merchant_key))

        return invalid_parameters

    def _payco_form_validate(self, data):
        cod_response = int(data.get('x_cod_response'))
        result = self.write({
            'acquirer_reference': data.get('x_ref_payco'),
            'date': fields.Datetime.now(),
        })
        signature = data.get('x_signature')
        tx = self.env['payment.transaction'].search([('reference', '=', data.get('x_extra2'))])
        shasign_check = self.acquirer_id._payco_generate_sign(signature, data)
        x_test_request = data.get('x_test_request')
        isTestPluginMode = 'yes' if data.get('x_extra4') == 'true' else 'no'
        x_approval_code = data.get('x_approval_code')
        x_cod_transaction_state = data.get('x_cod_transaction_state')
        isTestTransaction = 'yes' if x_test_request == 'TRUE' else 'no'
        isTestMode = 'true' if isTestTransaction == 'yes' else 'false'

        validation = False
        if float_compare(float(data.get('x_amount', '0.0')), tx.amount, 2) == 0:
            if isTestPluginMode == "yes":
                validation = True
            if isTestPluginMode == "no":
                if x_approval_code != "000000" and int(x_cod_transaction_state) == 1:
                    validation = True
                else:
                    if int(x_cod_transaction_state) != 1:
                        validation = True
                    else:
                        validation = False

        massage = ""
        if shasign_check == True and validation == True:
            if tx.state not in ['draft']:
                if cod_response not in [1,3]:
                    allowed_states = ('draft', 'authorized', 'pending')
                    target_state = 'draft'
                    (tx_to_process, tx_already_processed, tx_wrong_state) = self._filter_transaction_state(allowed_states, target_state)
                    massage = "second confirm ePayco"
                    tx_to_process.write({
                        'state': target_state,
                        'date': fields.Datetime.now(),
                        'state_message': massage,
                    })
                    tx_to_process.write({
                        'state': 'cancel',
                        'date': fields.Datetime.now(),
                        'state_message': massage,
                    })
                    self.manage_status_order(data.get('x_extra1'),'sale_order')
                else:
                    if tx.state in ['pending']:
                        if cod_response == 1:
                            self._set_transaction_done()

            else:
                if cod_response == 1:
                    self._set_transaction_done()
                elif cod_response == 3:
                    self._set_transaction_pending()
                else:
                    self.manage_status_order(data.get('x_extra1'),'sale_order')          
        else:
            if tx.state in ['done']:
                allowed_states = ('draft', 'authorized', 'pending','done')
                target_state = 'draft'
                (tx_to_process, tx_already_processed, tx_wrong_state) = self._filter_transaction_state(allowed_states, target_state)
                massage = "second confirm ePayco"
                tx_to_process.write({
                    'state': target_state,
                    'date': fields.Datetime.now(),
                    'state_message': massage,
                })
                tx_to_process.write({
                    'state': 'cancel',
                    'date': fields.Datetime.now(),
                    'state_message': massage,
                })
                self.manage_status_order(data.get('x_extra1'),'stock_picking', confirmation=True)
                self.manage_status_order(data.get('x_extra1'),'sale_order')
                self.manage_status_order(data.get('x_extra1'),'stock_move', confirmation=True)
            else:
                self.manage_status_order(data.get('x_extra1'),'sale_order')
   
        return result

    def query_update_status(self, table, values, selectors):
        """ Update the table with the given values (dict), and use the columns in
            ``selectors`` to select the rows to update.
        """
        UPDATE_QUERY = "UPDATE {table} SET {assignment} WHERE {condition} RETURNING id"
        setters = set(values) - set(selectors)    
        assignment=",".join("{0}='{1}'".format(s,values[s]) for s in setters)
        condition=" AND ".join("{0}='{1}'".format(s,selectors[s]) for s in selectors)
        query = UPDATE_QUERY.format(
            table=table,
            assignment=assignment,
            condition=condition,
        )
        self.env.cr.execute(query,values)
        self.env.cr.fetchall()

    def reflect_params(self, name, confirmation=False):
        """ Return the values to write to the database. """
        if not confirmation:
            return {'name': name}
        else:
            return {'origin': name}

    def manage_status_order(self,order_name, model_name, confirmation=False):
        condition = self.reflect_params(order_name , confirmation)
        params = {'state': 'draft'}
        self.query_update_status(model_name, params, condition)
        self.query_update_status(model_name, {'state': 'cancel'}, condition)
        self._set_transaction_cancel()