# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import sys

import requests
from odoo import _, http
from odoo.http import request, Response

_logger = logging.getLogger(__name__)

class EpaycoController(http.Controller):
    _return_url = '/payment/epayco/response'
    _confirm_url = '/payment/epayco/confirm'
    _proccess_url = '/payment/epayco/checkout'

    @http.route(_proccess_url, type='http', auth='public', methods=['GET', 'POST'], website=True, csrf=False, save_session=False)
    def epayco_checkout(self, **post):
        """ Epayco."""
        print(post)
        return request.render('payment_epayco.proccess', post)

    @http.route(
        _confirm_url, type='http', auth='public', methods=['POST'],  website=True, csrf=False, save_session=False
    )
    def epayco_backend_confirm(self, **post):
        return self._epayco_process_response(post,confirmation=True)

    @http.route(
        _return_url,  type='http', auth='public', methods=['GET'],  website=True, csrf=False, save_session=False
    )
    def epayco_backend_redirec(self, **post):
        return self._epayco_process_response(post)

    def _epayco_process_response(self, data, confirmation=False):
        if not confirmation:
            ref_epayco = data.get('ref_payco')
            if ref_epayco is None:
                return request.redirect('/shop/payment')
            url = 'https://secure.epayco.io/validation/v1/reference/%s' % (
                ref_epayco)
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json().get('data')
                if int(data.get('x_cod_response')) not in [1, 3]:
                    return request.redirect('/shop/payment')
                else:
                    tx_sudo = request.env['payment.transaction'].sudo()._get_tx_from_notification_data(
                        'epayco', data
                    )
                    tx_sudo._handle_notification_data('epayco', data)
                    return request.redirect('/payment/status')
            else:
                return request.redirect('/shop/payment')
        else:
            tx_sudo = request.env['payment.transaction'].sudo()._get_tx_from_notification_data(
                'epayco', data
            )
            tx_sudo._handle_notification_data('epayco', data)
            return Response(status=200)



