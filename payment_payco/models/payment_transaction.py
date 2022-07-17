# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import sys
from werkzeug import urls
from pprint import pprint

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo import http
from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment_payco.controllers.main import PaycoController

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    payco_payment_ref = fields.Char(string="ePayco Payment Reference")

    def _get_specific_rendering_values(self, processing_values):
        """ Override of payment to return ePayco-specific rendering values.

        Note: self.ensure_one() from `_get_processing_values`

        :param dict processing_values: The generic and specific processing values of the transaction
        :return: The dict of acquirer-specific processing values
        :rtype: dict
        """
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider != 'payco':
            return res

        base_url = self.acquirer_id.get_base_url()
        partner_first_name, partner_last_name = payment_utils.split_partner_name(self.partner_name)
        test = 'false' if self.state == 'enabled' else 'true'
        lang = 'es' if self.partner_lang == 'es_CO' else 'en'
        external = 'true' if self.acquirer_id.payco_checkout_type == 'standard' else 'false'
        split_reference = self.reference.split('-')
        reference = split_reference[0]
        sql = """select amount_tax from sale_order where name = '%s'
                        """ % (reference)
        http.request.cr.execute(sql)
        result = http.request.cr.fetchall() or []
        if not result:
            reference = self.reference
            sql = """select amount_tax from sale_order where name = '%s'
                        """ % (reference)
            http.request.cr.execute(sql)
            result = http.request.cr.fetchall() or []
            if result:
                (amount_tax) = result[0]
        else:
            (amount_tax) = result[0]        
        for tax_amount in amount_tax:
            tax = tax_amount
        base_tax = float(float(self.amount) - float(tax))

        tx = self.env['payment.transaction'].search([('reference', '=', self.reference)])

        return {
            'public_key': self.acquirer_id.payco_public_key,
            'address1': self.partner_address,
            'amount': self.amount,
            'tax': tax,
            'base_tax': base_tax,
            'city': self.partner_city,
            'country': self.partner_country_id.code,
            'currency_code': self.currency_id.name,
            'email': self.partner_email,
            'first_name': partner_first_name,
            'last_name': partner_last_name,
            "phone_number": tx.partner_id.phone.replace(' ', ''),
            'lang': lang,
            'checkout_external': external,
            "test": test,
            'confirmation_url': urls.url_join(base_url, '/payco/confirmation/backend'),
            'response_url': urls.url_join(base_url,'/payco/redirect/backend'),
            'api_url': urls.url_join(base_url, '/payment/payco/checkout'),
            'extra1': str(tx.id),
            'extra2': self.reference,
            'reference': str(reference)
        }

    @api.model
    def _get_tx_from_feedback_data(self, provider, data):
        """ Override of payment to find the transaction based on Paypal data.

        :param str provider: The provider of the acquirer that handled the transaction
        :param dict data: The feedback data sent by the provider
        :return: The transaction if found
        :rtype: recordset of `payment.transaction`
        :raise: ValidationError if the data match no transaction
        """
        tx = super()._get_tx_from_feedback_data(provider, data)
        if provider != 'payco':
            return tx
        try:
            tx_id = data.get('x_extra1')
            tx = self.search([('id', '=', int(tx_id)), ('provider', '=', 'payco')])
            if not tx:
                raise ValidationError(
                    "ePayco: " + _("No transaction found")
                )
        except Exception as e:
            raise ValidationError(
                    "ePayco: " + _("No transaction found")
                )
        return tx

    def _process_feedback_data(self, data):
        """ Override of payment to process the transaction based on Payco data.

        Note: self.ensure_one()

        :param dict data: The feedback data sent by the provider
        :return: None
        :raise: ValidationError if inconsistent data were received
        """
        super()._process_feedback_data(data)
        if self.provider != 'payco':
            return
        tx = ''
        if data:
            sql = """select state from sale_order where name = '%s'
                                        """ % (data.get('x_extra3'))
            http.request.cr.execute(sql)
            result = http.request.cr.fetchall() or []
            if result:
                (state) = result[0]
            for testMethod in state:
                tx = testMethod
            cod_response = int(data.get('x_cod_response'))
            if tx not in ['draft']:
                if cod_response not in [1, 3]:
                    self.manage_status_order(data.get('x_extra3'), 'sale_order')
                else:
                    if cod_response == 1:
                        self.payco_payment_ref = data.get('x_extra2')
                        self._set_done()
                        self._finalize_post_processing()
            else:
                if cod_response == 1:
                    self.payco_payment_ref = data.get('x_extra2')
                    self._set_done()
                    self._finalize_post_processing()
                elif cod_response == 3:
                    self._set_pending()
                else:
                    self.manage_status_order(data.get('x_extra3'),'sale_order')
                    self._set_canceled()


    def query_update_status(self, table, values, selectors):
        """ Update the table with the given values (dict), and use the columns in
            ``selectors`` to select the rows to update.
        """
        UPDATE_QUERY = "UPDATE {table} SET {assignment} WHERE {condition} RETURNING id"
        setters = set(values) - set(selectors)
        assignment = ",".join("{0}='{1}'".format(s, values[s]) for s in setters)
        condition = " AND ".join("{0}='{1}'".format(s, selectors[s]) for s in selectors)
        query = UPDATE_QUERY.format(
            table=table,
            assignment=assignment,
            condition=condition,
        )
        self.env.cr.execute(query, values)
        self.env.cr.fetchall()

    def reflect_params(self, name, confirmation=False):
        """ Return the values to write to the database. """
        if not confirmation:
            return {'name': name}
        else:
            return {'origin': name}

    def manage_status_order(self, order_name, model_name, confirmation=False):
        condition = self.reflect_params(order_name, confirmation)
        params = {'state': 'draft'}
        self.query_update_status(model_name, params, condition)
        self.query_update_status(model_name, {'state': 'cancel'}, condition)

