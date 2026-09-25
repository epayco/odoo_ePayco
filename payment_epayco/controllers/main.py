# Part of Odoo. See LICENSE file for full copyright and licensing details.

import hmac
import logging
import pprint
import re
import sys
import base64
from werkzeug.exceptions import Forbidden
from werkzeug import urls

from odoo import http, _
from odoo.http import request, Response
from odoo.exceptions import UserError, ValidationError
from odoo.addons.payment_epayco import const


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
        provider = request.env['payment.provider'].sudo().search(
            [
                ('code', '=', 'epayco'),
                ('company_id', 'in', [request.env.company.id, False]),
            ], limit=1
        )
        if not provider:
            raise Forbidden()  # SDK-1360: website.403 no esta registrada aqui (500 en vez de 403); Forbidden() no depende de una vista

        post = dict(post)

        reference = post.get('reference') or ''
        # SDK-1360: la referencia REAL de payment.transaction (con sufijo de
        # timestamp) llega en 'extra2', no en 'reference' -- ese campo solo trae
        # el nombre de la orden (p.ej. 'S00045'), reusado tal cual para los
        # campos de session_data que ePayco espera con ese formato
        # (name/description/invoice/extras.extra3), igual que ya hacia el JS
        # original. La busqueda de la transaccion debe hacerse por 'extra2'.
        tx_reference = post.get('extra2') or ''

        # SDK-1360: valida que `tx_reference` corresponda a una payment.transaction
        # real de este provider ANTES de crear una sesion de checkout con las
        # credenciales reales del comercio. Sin esto (hallazgo HIGH de
        # security-agent), esta ruta es publica/sin CSRF y cualquier visitante
        # anonimo podia usarla como proxy no autenticado hacia la API de
        # ePayco -- mandar un `reference` inventado bastaba para que Odoo, con
        # el JWT real del comercio, creara una sesion de checkout arbitraria
        # (monto, notify_url/return_url, datos de billing, todo controlado por
        # el atacante).
        tx_sudo = request.env['payment.transaction'].sudo().search([
            ('reference', '=', tx_reference), ('provider_code', '=', 'epayco'),
        ], limit=1)
        if not tx_sudo:
            raise Forbidden()  # SDK-1360: misma correccion que arriba, para el chequeo de reference/tx_sudo

        # El resto del payload tambien se recalcula desde la transaccion real
        # en vez de confiar en `post` -- mismo dato, misma fuente que ya usa
        # `PaymentTransaction._get_specific_rendering_values` para
        # return_url/confirm_url, ahora tambien para amount/currency/billing.
        plit_reference = tx_sudo.reference.split('-')
        tax = tx_sudo.get_tax('sale_order', plit_reference[0]) or tx_sudo.get_tax('account_move', plit_reference[0]) or 0
        amount = tx_sudo.amount
        base_tax = float(amount) - float(tax)
        notify_url = urls.url_join(tx_sudo.provider_id.get_base_url(), self._confirm_url)
        return_url = urls.url_join(tx_sudo.provider_id.get_base_url(), self._return_url)

        session_data = {
            'checkout_version': '2',
            'name': reference[:50],
            'description': reference[:50],
            'invoice': reference,
            'currency': (tx_sudo.currency_id.name or '').lower(),
            'amount': float(amount),
            'taxBase': float(base_tax),
            'tax': float(tax),
            'taxIco': 0,
            'country': 'CO',
            'lang': tx_sudo.provider_id.epayco_checkout_lang,
            'confirmation': notify_url,
            'response': return_url,
            'billing': {
                'name': tx_sudo.partner_name or '',
                'address': tx_sudo.partner_address or '',
                'email': tx_sudo.partner_email or '',
            },
            'autoclick': True,
            # 'ip': request.httprequest.remote_addr,
            'test': tx_sudo.provider_id.state == 'test',
            'extras': {
                'extra2': tx_sudo.reference,
                'extra3': plit_reference[0],
            },
            'extrasEpayco': {
                'extra5': 'P32',
            },
            'method': 'POST',
            'autoClick': False,
            'methodsDisable': [],
            'dues': 1,
            'noRedirectOnClose': True,
            'forceResponse': False,
            'uniqueTransactionPerBill': False,
            'config': {},
        }
        session_id = provider.sudo()._epayco_create_checkout_session(session_data)

        # SDK-1360: persistir aqui el session_id real como provider_reference --
        # es la unica referencia que el endpoint de consulta de estado
        # (/validation/v1/reference/{ref}) reconoce (confirmado en vivo contra la
        # API real: consultar por x_ref_payco devuelve 404, por este session_id
        # devuelve 200 con los datos reales de la transaccion). Se persiste apenas
        # se crea la sesion, sin esperar a ninguna notificacion -- es lo que le
        # permite al cron de reconciliacion (_cron_epayco_sync_pending_transactions)
        # encontrar algo que consultar incluso si el webhook nunca llega.
        if session_id and not tx_sudo.provider_reference:
            tx_sudo.provider_reference = session_id

        post.update({
            'session_id': session_id or '',
            'external': post.get('checkout_external'),
            'checkout_js_url': (
                const.EPAYCO_CHECKOUT_JS_TEST if provider.state == 'test'
                else const.EPAYCO_CHECKOUT_JS_PROD
            ),
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
                provider = request.env['payment.provider'].sudo().search(
                    [
                        ('code', '=', 'epayco'),
                        ('company_id', 'in', [request.env.company.id, False]),
                    ], limit=1
                )
                data = provider._epayco_get_transaction_status(ref_epayco)
                _logger.info("data validation:\n%s", pprint.pformat(data))
                if data is None:
                    return request.redirect('/shop/payment')
                if int(data.get('x_cod_response')) not in [1, 3]:
                    return request.redirect('/shop/payment')
                else:
                    # `PaymentTransaction._epayco_process_notification_data`.
                    request.env['payment.transaction']._epayco_process_notification_data(data)
                    # Handle the notification data
                    return request.redirect('/payment/status')
            else:
                request.env['payment.transaction']._epayco_process_notification_data(data)
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
