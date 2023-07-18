# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import sys
from pprint import pprint

from odoo.fields import Command

from requests.exceptions import ConnectionError, HTTPError
from werkzeug import urls
import requests
from odoo import _, http
from odoo.exceptions import ValidationError
from odoo.http import request, Response
from odoo.addons.payment.controllers import portal as payment_portal
from odoo.addons.payment.controllers.post_processing import PaymentPostProcessing

import json
_logger = logging.getLogger(__name__)

class EpaycoController(http.Controller):
    _return_url = '/payment/epayco/response'
    _confirm_url = '/payment/epayco/confirm'
    _proccess_url = '/payment/epayco/checkout'

    @http.route(['/payment/epayco/checkout'], type='http', auth='public', website=True, csrf=False, save_session=False)
    def epayco_checkout(self, **post):
        """ Epayco."""
        print(post)
        return request.render('payment_epayco.proccess', post)

    @http.route(
        _confirm_url, type='http', auth='public', methods=['POST'], csrf=False
    )
    def epayco_backend_confirm(self, **post):
        return self._epayco_process_response(post,confirmation=True)

    @http.route(
        _return_url, type='http', auth='public', website=True, csrf=False, save_session=False
    )
    def epayco_backend_redirec(self, **post):
        return self._epayco_process_response(post)

    def _epayco_process_response(self, data, confirmation=False):
        if not confirmation:
            ref_epayco = data.get('ref_payco')
            if ref_epayco is None:
                return request.redirect('/shop/payment')
            url = 'https://secure.epayco.co/validation/v1/reference/%s' % (
                ref_epayco)
            response = requests.get(url)
            print("ePayco ref_payco")
            print("================= response =======================")
            print(response)
            if response.status_code == 200:
                data = response.json().get('data')
                
                request.env['payment.transaction'].sudo()._handle_feedback_data('epayco', data)
                return request.redirect('/payment/status')
            else:
                return request.redirect('/shop/payment')
        else:
            print("ePayco ref_payco")
            print("================== confirmation ======================")
            request.env['payment.transaction'].sudo()._handle_feedback_data('epayco', data)
            return Response(status=200)



