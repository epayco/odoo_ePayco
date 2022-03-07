# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import hashlib
import uuid
from werkzeug import urls

from odoo import api, fields, models, _
from odoo.addons.payment.models.payment_acquirer import ValidationError
from odoo.tools.float_utils import float_compare
import logging

_logger = logging.getLogger(__name__)

class PaymentAcquirerEpayco(models.Model):
    _inherit = 'payment.acquirer'
    provider = fields.Selection(selection_add=[('epayco', 'Epayco')])

    epayco_p_cust_id = fields.Char(string='P_CUST_ID', required_if_provider='epayco', groups='base.group_user')
    epayco_p_key = fields.Char(string='P_KEY', required_if_provider='epayco', groups='base.group_user')
    epayco_public_key = fields.Char(string='PUBLICK_KEY', required_if_provider='epayco', groups='base.group_user')
    epayco_checkout_type = fields.Selection(
        selection=[('onpage', 'Onpage Checkout'),
                   ('standard', 'Standard Checkout')],
        required_if_provider='epayco',
        string='Checkout Type',
        default='onpage')

    def epayco_form_generate_values(self, values):
        self.ensure_one()
        env_test = 'false' if self.state == 'prod' else 'true'
        partner_lang = values.get('partner') and values['partner'].lang
        lang = 'es' if 'es' in partner_lang else 'en'
        country = values.get('partner_country').code.lower()
        epayco_checkout_external = (
            'false' if self.epayco_checkout_type == 'onpage' else 'true')
        tx = self.env['payment.transaction'].search([('reference', '=', values.get('reference'))])
        if tx.state not in ['done', 'pending']:
            tx.reference = str(uuid.uuid4())
        base_url = self.get_base_url()
        url_confirmation = urls.url_join(base_url, '/payment/epayco/confirmation/')
        url_response = urls.url_join(base_url, '/payment/epayco/response/')
        epayco_tx_values = dict(values)
        split_reference = epayco_tx_values.get('reference').split('-')
        order = ''
        tax = values['partner'].last_website_so_id.amount_tax
        base_tax = values['partner'].last_website_so_id.amount_undiscounted
        amount = values['partner'].last_website_so_id.amount_total
        if split_reference:
            order = split_reference[0]
        epayco_tx_values.update({
            'public_key': self.epayco_public_key,
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
            'epayco_checkout_external': epayco_checkout_external,
            'epayco_env_test': env_test,
            'epayco_lang': lang,
            'response_url': url_response,
            'url_confirmation': url_confirmation,
            'extra1': env_test,
            'extra2': values['reference'],
        })
        return epayco_tx_values

    def epayco_get_form_action_url(self):
        self.ensure_one()
        return '/payment/epayco/checkout/'


    def _epayco_generate_sign(self, values):
        """ Generate the shasign for incoming or outgoing communications.
        :param self: the self browse record. It should have a shakey in shakey out
        :param string inout: 'in' (odoo contacting epayco) or 'out' (epayco
                             contacting odoo).
        :param dict values: transaction values

        :return string: shasign
        """
        self.ensure_one()
        p_key = self.epayco_p_key
        x_ref_payco = values.get('x_ref_payco')
        x_transaction_id = values.get('x_transaction_id')
        x_amount = values.get('x_amount')
        x_currency_code = values.get('x_currency_code')
        hash_str_bytes = bytes('%s^%s^%s^%s^%s^%s' % (
            self.epayco_p_cust_id,
            p_key,
            x_ref_payco,
            x_transaction_id,
            x_amount,
            x_currency_code), 'utf-8')
        hash_object = hashlib.sha256(hash_str_bytes)
        hash = hash_object.hexdigest()
        return hash


class PaymentTransactionEpayco(models.Model):
    _inherit = 'payment.transaction'

    @api.model
    def _epayco_form_get_tx_from_data(self, data):
        """ Given a data dict coming from epayco, verify it and find the related
        transaction record. """
        reference = data.get('x_extra2')
        signature = data.get('x_signature')
        if not reference or not reference or not signature:
            raise ValidationError(_('Epayco: received data with missing reference (%s) or signature (%s)') % (reference, signature))

        transaction = self.search([('reference', '=', reference)])

        if not transaction:
            error_msg = (_('Epayco: received data for reference %s; no order found') % (reference))
            raise ValidationError(error_msg)
        elif len(transaction) > 1:
            error_msg = (_('Epayco: received data for reference %s; multiple orders found') % (reference))
            raise ValidationError(error_msg)        

        return transaction

    def _epayco_form_get_invalid_parameters(self, data):
        invalid_parameters = []
            # check what is buyed
        if int(self.acquirer_id.epayco_p_cust_id) != int(data.get('x_cust_id_cliente')):
            invalid_parameters.append(
                ('Customer ID', data.get('x_cust_id_cliente'), self.acquirer_id.epayco_p_cust_id))
        return invalid_parameters

    def _epayco_form_validate(self, data):
        cod_response = int(data.get('x_cod_response'))
        result = self.write({
            'acquirer_reference': data.get('x_ref_payco'),
            'date': fields.Datetime.now(),
        })
        # verify signature
        reference = data.get('x_extra2')
        signature = data.get('x_signature')
        shasign_check = self.acquirer_id._epayco_generate_sign(data)
        tx = self.env['payment.transaction'].search([('reference', '=', reference)])
        x_test_request = data.get('x_test_request')
        isTestPluginMode = 'yes' if data.get('x_extra1') == 'true' else 'no'
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
        if signature == shasign_check and validation == True:
            if tx.state not in ['draft']:
                if cod_response not in [1,3]:
                    allowed_states = ('draft', 'authorized', 'pending')
                    target_state = 'cancel'
                    (tx_to_process, tx_already_processed, tx_wrong_state) = self._filter_transaction_state(allowed_states, target_state)
                    massage = "second confirm ePayco"
                    tx_to_process.write({
                        'state': target_state,
                        'date': fields.Datetime.now(),
                        'state_message': massage,
                    })
                    self.manage_status_order(data.get('x_description'),'sale_order')
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
                    self.manage_status_order(data.get('x_description'),'sale_order')
        else:
            if tx.state in ['done']:
                allowed_states = ('draft', 'authorized', 'pending','done')
                target_state = 'cancel'
                (tx_to_process, tx_already_processed, tx_wrong_state) = self._filter_transaction_state(allowed_states, target_state)
                massage = "second confirm ePayco"
                tx_to_process.write({
                    'state': target_state,
                    'date': fields.Datetime.now(),
                    'state_message': massage,
                })
                self.manage_status_order(data.get('x_description'),'stock_picking', confirmation=True)
                self.manage_status_order(data.get('x_description'),'sale_order')
                self.manage_status_order(data.get('x_description'),'stock_move', confirmation=True)
            else: 
                self.manage_status_order(data.get('x_description'),'sale_order')

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