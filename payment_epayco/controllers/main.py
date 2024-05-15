# Part of Odoo. See LICENSE file for full copyright and licensing details.

import hmac
import logging
import pprint
import re
import requests
from werkzeug.exceptions import Forbidden

from odoo import http
from odoo.http import request, Response

_logger = logging.getLogger(__name__)

class EpaycoController(http.Controller):
    _return_url = '/payment/epayco/response'
    _confirm_url = '/payment/epayco/confirm'
    _proccess_url = '/payment/epayco/checkout'

    @http.route(
        '/payment/epayco/checkout', type='http', auth='public',
        methods=['GET', 'POST'], csrf=False
    )  # Redirect are made with GET requests only. Webhook notifications can be set to GET or POST.
    def epayco_checkout(self, **post):
        """ Epayco checkout."""
        return request.render('payment_epayco.proccess', post)

    @http.route(
        '/payment/epayco/response', type='http', auth='public',
        methods=['GET', 'POST'], csrf=False
    )  # Redirect are made with GET requests only. Webhook notifications can be set to GET or POST.
    def epayco_backend_redirec(self, **post):
        return self._epayco_process_response(post)

    @http.route(
        '/payment/epayco/confirm', type='http', auth='public',
        methods=['GET', 'POST'], csrf=False
    )  # Redirect are made with GET requests only. Webhook notifications can be set to GET or POST.
    def epayco_backend_confirm(self, **post):
        return self._epayco_process_response(post, confirmation=True)

    def _epayco_process_response(self, data, confirmation=False):
        _logger.info("handling redirection from epayco with data:\n%s", pprint.pformat(data))
        data_normalize = self._normalize_data_keys(data)
        if not confirmation:
            # Check the integrity of the notification_return_url
            ref_epayco = data.get('ref_epayco')
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
                    # Handle the notification data
                    return request.redirect('/payment/status')
            else:
                return request.redirect('/shop/payment')
        else:
            tx_sudo = request.env['payment.transaction'].sudo()._get_tx_from_notification_data(
                'epayco', data
            )
            tx_sudo._handle_notification_data('epayco', data)
            return Response(status=200)


    @staticmethod
    def _normalize_data_keys(data):
        return {re.sub(r'.*\.', '', k.upper()): v for k, v in data.items()}

    @staticmethod
    def _verify_notification_signature(notification_data, received_signature, tx_sudo):
        # Check for the received signature
        if not received_signature:
            _logger.warning("received notification with missing signature")
            raise Forbidden()

        # Compare the received signature with the expected signature computed from the data
        expected_signature = tx_sudo.provider_id._epayco_generate_signature(notification_data)
        if not hmac.compare_digest(received_signature, expected_signature.upper()):
            _logger.warning("received notification with invalid signature")
            raise Forbidden()
