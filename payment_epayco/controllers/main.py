# Part of Odoo. See LICENSE file for full copyright and licensing details.

import hmac
import logging
import pprint
import re
import requests
import sys
import base64
from werkzeug.exceptions import Forbidden

from odoo import http, _
from odoo.http import request, Response
from odoo.exceptions import UserError, ValidationError


_logger = logging.getLogger(__name__)

class EpaycoController(http.Controller):
    _return_url = '/payment/epayco/response'
    _confirm_url = '/payment/epayco/confirm'
    _proccess_url = '/payment/epayco/checkout'

    @http.route(
        '/payment/epayco/checkout', type='http', auth='public',
        methods=['GET', 'POST'], csrf=False, website=True
    )
    def epayco_checkout(self, **post):
        """ Epayco checkout."""
        provider = request.env['payment.provider'].sudo().search([('code', '=', 'epayco')], limit=1)
        if not provider:
            return request.render('website.403')  # o maneja el error como prefieras
        
        epayco_token = provider.sudo().get_epayco_token()
        
        post = dict(post)
        post.update({
            'public_key': provider.epayco_public_key,
            'private_key': provider.epayco_private_key,
            'epayco_token': epayco_token,
        })
        return request.render('payment_epayco.proccess', post)

    @http.route(
        '/payment/epayco/response', type='http', auth='public',
        methods=['GET'], csrf=False
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
        try:
            _logger.info("handling redirection from epayco with data:\n%s", pprint.pformat(data))
            data_normalize = self._normalize_data_keys(data)
            if not confirmation:
                # Check the integrity of the notification_return_url
                ref_epayco = data.get('ref_epayco') or data.get('ref_payco')
                _logger.info("ref payco:\n%s", ref_epayco)
                if ref_epayco is None or ref_epayco == "undefined":
                    return request.redirect('/shop/payment')
                url = 'https://secure.epayco.co/validation/v1/reference/%s' % (
                    ref_epayco)
                response = requests.get(url)
                _logger.info("data validation:\n%s", pprint.pformat(response))
                if response.status_code == 200:
                    data = response.json().get('data')
                    if int(data.get('x_cod_response')) not in [1, 3]:
                        return request.redirect('/shop/payment')
                    else:
                        tx_sudo = request.env['payment.transaction'].sudo()._get_tx_from_notification_data(
                            'epayco', data
                        )
                        self._verify_notification_signature(data, tx_sudo)
                        tx_sudo._handle_notification_data('epayco', data)
                        # Handle the notification data
                        return request.redirect('/payment/status')
                else:
                    return request.redirect('/shop/payment')
            else:
                tx_sudo = request.env['payment.transaction'].sudo()._get_tx_from_notification_data(
                    'epayco', data
                )
                self._verify_notification_signature(data, tx_sudo)
                tx_sudo._handle_notification_data('epayco', data)
                return Response(status=200)
        except KeyError as e:
            # Manejar errores por claves faltantes en los datos
            _logger.error("KeyError encountered in comfirmation_data: %s", e)
            raise ValidationError(_("Invalid comfirmation data: Missing key %s.") % str(e))

        except ValidationError as e:
            # Re-lanzar errores de validación con más contexto si es necesario
            _logger.warning("Validation error while processing epayco confirmation: %s", e)
            raise e

        except Exception as e:
            # Capturar cualquier otra excepción inesperada
            _logger.exception("Unexpected error while retrieving ref_payco.")
            raise UserError(_("An unexpected error occurred: %s") % str(e))


    @staticmethod
    def _normalize_data_keys(data):
        return {re.sub(r'.*\.', '', k.upper()): v for k, v in data.items()}

    @staticmethod
    def _verify_notification_signature(notification_data, tx_sudo):
        # Check for the received signature
        received_signature = notification_data.get('x_signature')
        if not received_signature:
            _logger.warning("received notification with missing signature")
            raise ValidationError(
                "epayco: " + _("No signature found %s.", received_signature)
            )

        # Compare the received signature with the expected signature computed from the data
        expected_signature = tx_sudo.provider_id._epayco_generate_signature(notification_data, incoming=True)
        if received_signature != expected_signature:
            _logger.warning("received notification with invalid signature")
            raise ValidationError(
                "Epayco: " + _(
                    "Invalid sign: received %(sign)s, expected %(check)s.",
                    sign=received_signature, check=expected_signature
                )
            )
