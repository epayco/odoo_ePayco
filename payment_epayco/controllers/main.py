# -*- coding: utf-8 -*-
# Copyright 2019 ePayco.co
# - Manuel Marquez <buzondemam@gmail.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging
import pprint
import requests
import werkzeug

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class EpaycoController(http.Controller):
    _response_url = '/payment/epayco/response/'
    _confirmation_url = '/payment/epayco/confirmation/'

    @http.route(
        ['/payment/epayco/checkout/'], type='http', csrf=False, website=True)
    def epayco_checkout(self, **post):
        """Render template to redirect to ePayco checkout."""
        order = request.website.sale_get_order()
        post.update({
            'amount_tax': order.amount_tax,
            'amount_untaxed': order.amount_untaxed,
        })
        return request.render('payment_epayco.checkout', post)

    @http.route(
        ['/payment/epayco/response/', '/payment/epayco/confirmation/'],
        type='http',
        csrf=False,
        website=True)
    def epayco_return_url(self, **post):
        """Process response from ePayco after process payment."""
        ref_payco = post.get('ref_payco')
        url = 'https://secure.epayco.co/validation/v1/reference/%s' % ref_payco
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json().get('data')
            _logger.info('Beginning form_feedback with post data %s',
                         pprint.pformat(data))
            request.env['payment.transaction'].sudo().form_feedback(
                data, 'epayco')
            return werkzeug.utils.redirect('/payment/process')
        _logger.warning('ePayco: Request to API ePayco failed.')
