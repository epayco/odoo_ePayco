# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint
import requests
import werkzeug
import sys

from odoo import http
from odoo.http import request, Response

_logger = logging.getLogger(__name__)


class PaycoController(http.Controller):
    @http.route(['/payment/payco/checkout'], type='http', auth='public', website=True, csrf=False, save_session=False)
    def payco_checkout(self, **post):
        """ Epayco."""
        return request.render('payment_epayco.checkout', post)
        #return request.render('payment_payco.checkout', post)

    @http.route(
        ['/payment/payco/response/'],
        type='http',
        website=True,
        csrf=False)
    def payco_return_url(self, **post):
        """Process response from ePayco after process payment."""
        return self._payco_process_response(post)

    @http.route(
        ['/payment/payco/confirmation/'],
        type='http',
        csrf=False,
        website=True,
        auth='public')
    def payco_payment_confirmation_url(self, **post):
        """Process payment confirmation from ePayco."""
        return self._payco_process_response(post, confirmation=True)

    def _payco_process_response(self, data, confirmation=False):
        if not confirmation:
            ref_payco = data.get('ref_payco')
            if ref_payco is None:
                _logger.debug('User error in ePayco checkout: %s', data)
                return werkzeug.utils.redirect('/shop/payment')
            url = 'https://secure.epayco.io/validation/v1/reference/%s' % (
                ref_payco)
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json().get('data')
                _logger.info('Beginning form_feedback with post data %s',
                             pprint.pformat(data))
                request.env['payment.transaction'].sudo().form_feedback(
                    data, 'payco')
                return werkzeug.utils.redirect('/payment/process')
        else:
            request.env['payment.transaction'].sudo().form_feedback(
                data, 'payco')
            self._post_process_tx(data)
            return Response(status=200)

    def _post_process_tx(self, data):
        """Post process transaction to confirm the sale order and
        to generate the invoices if needed."""
        tx_reference = data.get('x_extra2')
        payment_transaction = request.env['payment.transaction'].sudo()
        tx = payment_transaction.search([('reference', '=', tx_reference)])
        if not tx:
            _logger.exception('Transaction post processing failed. '
                              'Not found any transaction with reference %s',
                              tx_reference)
        if tx.state == 'done':
            return tx.sudo()._post_process_after_done()
        elif tx.state != 'pending':
            return tx.sudo()._log_payment_transaction_received()