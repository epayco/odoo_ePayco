# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint
import uuid
import socket
import sys
from datetime import timedelta

from lxml import etree, objectify
from werkzeug import urls

from odoo import _, api, fields, models, http
from odoo.http import request
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_repr, float_compare
from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment_epayco import const
from odoo.addons.payment_epayco.controllers.main import EpaycoController


_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    # Método eliminado, revertido a estado original
    _inherit = 'payment.transaction'

    @api.model
    def _compute_reference(self, provider_code, prefix=None, separator='-', **kwargs):
        if provider_code != 'epayco':
            return super()._compute_reference(provider_code, prefix=prefix, **kwargs)

        if not prefix:
            prefix = self.sudo()._compute_reference_prefix(provider_code, separator, **kwargs) or None
        prefix = payment_utils.singularize_reference_prefix(prefix=prefix, max_length=40)
        return super()._compute_reference(provider_code, prefix=prefix, **kwargs)

    def _get_specific_processing_values(self, processing_values):
        res = super()._get_specific_processing_values(processing_values)
        if self.provider_code != 'epayco':
            return res

        if self.operation in ('online_token', 'offline'):
            return {}

        return self._get_specific_rendering_values(self)

    def _get_specific_rendering_values(self, processing_values):
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != 'epayco':
            return res
        plit_reference = self.reference.split('-')
        tax = 0
        is_tax = self.get_tax('sale_order', plit_reference[0])
        if is_tax:
            tax = is_tax
        else:
            is_tax = self.get_tax('account_move', plit_reference[0])
            if is_tax:
                tax = is_tax

        hostname = socket.gethostname()
        ip_address = socket.gethostbyname(hostname)
        client_ip = request.httprequest.remote_addr
        #amount = float_repr(processing_values['amount'], self.currency_id.decimal_places or 2)
        amount = self.amount
        base_tax = float(amount) - float(tax)
        external = 'true' if self.provider_id.epayco_checkout_type == 'standard' else 'false'
        test = 'true' if self.provider_id.state == 'test' else 'false'
        return_url = urls.url_join(self.provider_id.get_base_url(), EpaycoController._return_url)
        confirm_url = urls.url_join(self.provider_id.get_base_url(), EpaycoController._confirm_url)
        api_url = urls.url_join(self.provider_id.get_base_url(), EpaycoController._proccess_url)
        language = self.partner_lang[0:2]
        rendering_values = {
            # SDK-1360: public_key/private_key removidos de aqui -- redirect_form ya no los expone
            # en HTML plano (ver views/payment_epayco_templates.xml).
            "amount": str(amount),
            "tax": str(tax),
            "base_tax": str(base_tax),
            "currency": self.currency_id.name,
            "email": self.partner_email or '',
            "firstname": self.partner_name or '',
            "reference": str(plit_reference[0]),
            "lang_checkout": self.provider_id.epayco_checkout_lang,
            "checkout_external": external,
            "test": test,
            "response_url": return_url,
            "confirmation_url": confirm_url,
            "extra2": self.reference,
            "order_name": str(plit_reference[0]),
            "ip": ip_address,
            "client_ip": client_ip,
            'address': self.partner_address or '',
            'zip': self.partner_zip or '',
            'city': self.partner_city or '',
            'country': self.partner_country_id.code or '',
            'cellphone': self.partner_phone or '',
            'total': payment_utils.to_minor_currency_units(self.amount, None, 2),
            'language': language,
            'url': return_url,
            'PM': const.PAYMENT_METHODS_MAPPING.get(
                self.payment_method_code, self.payment_method_code
            ),
        }
        rendering_values.update({
            'api_url': api_url,
        })
        return rendering_values

    def _get_tx_from_notification_data(self, provider_code, notification_data):
        try:
            tx = super()._get_tx_from_notification_data(provider_code, notification_data)
            if provider_code != 'epayco' or len(tx) == 1:
                return tx

            reference = notification_data.get('x_extra2')
            name = notification_data.get('x_extra3')
            amount = notification_data.get('x_amount')
            
            tx = self.search([('reference', '=', reference), ('provider_code', '=', 'epayco')])
            if not tx:
                raise ValidationError(
                    "epayco: " + _("No transaction found matching reference %s.", reference)
                )
            # SDK-1360: NO persistir aqui x_ref_payco (el ID numerico interno de
            # ePayco) como provider_reference -- es un identificador distinto del
            # que acepta el endpoint de consulta de estado
            # (/validation/v1/reference/{ref}), que exige la referencia de la
            # SESION de checkout (el mismo valor que sessionId, un hex largo).
            # Esa referencia se persiste al crear la sesion
            # (EpaycoController.epayco_checkout), no aqui -- confirmado en vivo:
            # consultar por x_ref_payco devuelve 404 "Checkout record not
            # found", consultar por la referencia de sesion real devuelve 200.

            order = self.env['sale.order'].sudo().search([('name', '=', name)], limit=1)
            
            if order:
                order_total = order.amount_total
                _logger.info("order_total:\n%s", pprint.pformat(order_total))
                order_tax = order.amount_tax
                _logger.info("order_tax:\n%s", pprint.pformat(order_tax))
                if float(order_total) != float(amount):
                    raise ValidationError(
                        "epayco: " + _("los montos no coinciden")
                    )
            else:
                raise ValidationError(
                    "epayco: " + _("Orden no encontrada")
                )    
            return tx
        except KeyError as e:
            # Manejar errores por claves faltantes en los datos
            _logger.error("KeyError encountered in notification_data: %s", e)
            raise ValidationError(_("Invalid notification data: Missing key %s.") % str(e))

        except ValidationError as e:
            # Re-lanzar errores de validación con más contexto si es necesario
            _logger.warning("Validation error while processing epayco notification: %s", e)
            raise e

        except Exception as e:
            # Capturar cualquier otra excepción inesperada
            _logger.exception("Unexpected error while retrieving transaction.")
            raise UserError(_("An unexpected error occurred: %s") % str(e))

    def _process_notification_data(self, notification_data):
        try:
            super()._process_notification_data(notification_data)
            # Update the payment state.
            order_id = notification_data.get('order_id')
            #order = self.env['sale.order'].sudo().browse(order_id)
            name = notification_data.get('x_extra3')
            order = self.env['sale.order'].sudo().search([('name', '=', name)], limit=1)
            payment_status = notification_data.get('x_cod_response')
            _logger.info("order_status:\n%s", pprint.pformat(order.state))
            _logger.info("invoice_status :\n%s", pprint.pformat(order.invoice_status))
            _logger.info("payment_status :\n%s", payment_status)
            #if payment_status in const.PAYMENT_STATUS_MAPPING['pending']:
            if int(payment_status) in [3]:
                self._set_pending()
            #elif payment_status in const.PAYMENT_STATUS_MAPPING['done']:
            elif int(payment_status) in [1]:
                # SDK-1360: reintentos de PSE dentro de la MISMA sesion de
                # checkout de ePayco (rechazar y volver a intentar sin salir
                # del widget) reusan la misma referencia de transaccion --
                # llegan dos webhooks distintos para el mismo tx: primero
                # "Rechazada" (cancela la tx), despues "Aceptada" (la
                # aprobacion real del reintento). Sin extra_allowed_states,
                # el guard de estados de Odoo (cancel -> done no esta en la
                # lista default de _set_done) rechaza la escritura en
                # silencio (WARNING, no excepcion) y la tx queda cancel para
                # siempre aunque el banco si aprobo -- confirmado en vivo
                # contra un pago real (orden S00080, dos webhooks reales del
                # mismo x_extra2, 90s de diferencia). Sin este fix, la orden
                # igual se confirmaba (el bloque de abajo no dependia del
                # resultado de _set_done), dejando la transaccion mostrando
                # cancel pese a que el pedido si se facturo.
                self._set_done(extra_allowed_states=('cancel',))
                # SDK-1360: 'draft' y 'sent' (Quotation Sent) son ambos estados no
                # confirmados de sale.order -- un pedido real de website_sale suele
                # quedar en 'sent', no 'draft', antes del pago (confirmado con un
                # pago real via el cron de reconciliacion: la transaccion paso a
                # 'done' pero la orden se quedo en 'sent' porque este chequeo solo
                # cubria 'draft'). action_confirm() es correcto para cualquiera de
                # los dos. Solo se confirma si la tx realmente quedo 'done' -- si
                # _set_done() no pudo aplicar el cambio por algun otro estado no
                # contemplado, no se factura una orden sobre una transaccion que
                # en realidad no se confirmo.
                if self.state == 'done' and order.state in ('draft', 'sent'):
                    self._epayco_confirm_and_invoice_order(order)
            #elif payment_status in const.PAYMENT_STATUS_MAPPING['cancel']:
            elif int(payment_status) in [2,4,9,10,11]:
                self._set_canceled()
            else:  # Classify unknown payment statuses as `error` tx state
                _logger.info(
                    "received data with invalid payment status (%s) for transaction with reference %s",
                    payment_status, self.reference
                )
                self._set_error(
                    "epayco: " + _("Received data with invalid payment status: %s", payment_status)
                )
        except KeyError as e:
            # Manejar errores por claves faltantes en los datos
            _logger.error("KeyError encountered in upload order status: %s", e)
            raise ValidationError(_("Invalid notification data: Missing key %s.") % str(e))

        except ValidationError as e:
            # Re-lanzar errores de validación con más contexto si es necesario
            _logger.warning("Validation error while uploading order status: %s", e)
            raise e

        except Exception as e:
            # Capturar cualquier otra excepción inesperada
            _logger.exception("Unexpected error while upload transaction.")
            raise UserError(_("An unexpected error occurred: %s") % str(e))

    def _epayco_confirm_and_invoice_order(self, order):
        try:
            with self.env.cr.savepoint():
                order.action_confirm()  # Confirmar la orden
                # Opcional: Generar y validar la factura
                if order.invoice_status == 'to invoice':
                    invoice = order._create_invoices()
                    invoice.action_post()
        except Exception:
            _logger.exception(
                "epayco: payment for order %s (tx reference %s) was "
                "approved and marked as done, but the order could "
                "not be auto-confirmed/invoiced. It requires manual "
                "confirmation.",
                order.name, self.reference,
            )
            order.message_post(body=_(
                "ePayco aprobo el pago de esta orden (referencia de "
                "transaccion %s), pero no se pudo confirmar/facturar "
                "automaticamente. Confirme la orden manualmente.",
                self.reference,
            ))

    @api.model
    def _epayco_process_notification_data(self, data):
        tx_sudo = self.sudo()._get_tx_from_notification_data('epayco', data)
        EpaycoController._verify_notification_signature(data, tx_sudo)
        tx_sudo._handle_notification_data('epayco', data)
        return tx_sudo

    @api.model
    def _cron_epayco_sync_pending_transactions(self):
        if not self.env['payment.provider'].sudo().search_count(
            [('code', '=', 'epayco')]
        ):
            return

        now = fields.Datetime.now()
        min_threshold = now - timedelta(
            minutes=const.EPAYCO_RECONCILE_MIN_AGE_MINUTES
        )
        max_threshold = now - timedelta(
            minutes=const.EPAYCO_RECONCILE_MAX_AGE_MINUTES
        )

        stuck_txs = self.sudo().search([
            ('provider_code', '=', 'epayco'),
            ('state', '=', 'pending'),
            ('create_date', '<=', min_threshold),
            ('create_date', '>', max_threshold),
        ], order='create_date asc', limit=const.EPAYCO_RECONCILE_BATCH_SIZE)
        for tx in stuck_txs:
            if not tx.provider_reference:
                _logger.warning(
                    "epayco: cannot reconcile transaction %s stuck in "
                    "pending since %s: no ePayco reference was ever "
                    "captured for it (no notification -- not even a "
                    "pending one -- ever reached Odoo for this "
                    "transaction). Needs manual follow-up.",
                    tx.reference, tx.create_date,
                )
                continue
            try:
                data = tx.provider_id._epayco_get_transaction_status(tx.provider_reference)
                if not data:
                    _logger.info(
                        "epayco: reconciliation query for transaction %s "
                        "(ref_payco %s) returned no data; will retry on "
                        "the next cron run.",
                        tx.reference, tx.provider_reference,
                    )
                    continue
                self._epayco_process_notification_data(data)
            except ValidationError:
                _logger.exception(
                    "epayco: data integrity error reconciling transaction "
                    "%s (ref_payco %s) -- invalid signature, amount "
                    "mismatch or order not found. Needs review.",
                    tx.reference, tx.provider_reference,
                )
            except Exception:
                # Error transitorio (red, timeout, ePayco caido, etc.):
                # se reintenta solo, sin intervencion, en una corrida
                # posterior del cron.
                _logger.exception(
                    "epayco: transient error reconciling transaction %s "
                    "(ref_payco %s); will retry on a later cron run.",
                    tx.reference, tx.provider_reference,
                )

        # Mas alla del tope maximo: dejar de consultar a ePayco, solo
        # marcar para revision manual (una vez, no en cada corrida).
        expired_txs = self.sudo().search([
            ('provider_code', '=', 'epayco'),
            ('state', '=', 'pending'),
            ('create_date', '<=', max_threshold),
        ])
        for tx in expired_txs:
            self._epayco_flag_reconciliation_window_expired(tx)

    def _epayco_flag_reconciliation_window_expired(self, tx):

        name = tx.reference.split('-')[0] if tx.reference else False
        order = (
            self.env['sale.order'].sudo().search([('name', '=', name)], limit=1)
            if name else self.env['sale.order']
        )

        # SDK-1360: el dedup original buscaba solo `tx.reference` en el body del
        # mensaje -- pero Odoo (el modulo `payment` core, no este) ya postea
        # automaticamente, al crear CUALQUIER transaccion, un mensaje generico
        # "A transaction with reference <reference> has been initiated (Epayco)."
        # que tambien contiene esa referencia como substring. Eso hacia que
        # `already_flagged` diera True para CUALQUIER transaccion real que
        # hubiera pasado por el checkout normal -- antes incluso de que este
        # metodo llegara a postear su propio mensaje -- dejando el aviso de
        # "ventana de reconciliacion expirada" muerto en la practica (nunca se
        # disparaba). Confirmado en vivo por odoo-qa-agent contra transacciones
        # reales. El marcador ahora exige ademas una frase fija unica de ESTE
        # mensaje especifico, no solo la referencia.
        expired_marker = 'dejo de reconsultarla automaticamente'
        already_flagged = bool(
            order and tx.reference and order.message_ids.filtered(
                lambda m: tx.reference in (m.body or '') and expired_marker in (m.body or '')
            )
        )
        if already_flagged:
            return

        _logger.warning(
            "epayco: transaction %s has been 'pending' for more than %s "
            "minutes without a resolution from epayco; the reconciliation "
            "cron will stop querying epayco for it. Needs manual "
            "follow-up.",
            tx.reference, const.EPAYCO_RECONCILE_MAX_AGE_MINUTES,
        )
        if order:
            order.message_post(body=_(
                "La transaccion de ePayco %(ref)s sigue 'pendiente' "
                "despues de %(minutes)s minutos sin confirmacion. El "
                "cron de reconciliacion dejo de reconsultarla "
                "automaticamente; revise manualmente el estado del "
                "pago.",
                ref=tx.reference,
                minutes=const.EPAYCO_RECONCILE_MAX_AGE_MINUTES,
            ))

    def _epayco_tokenize_from_notification_data(self, notification_data):
        token = self.env['payment.token'].create({
            'provider_id': self.provider_id.id,
            'payment_method_id': self.payment_method_id.id,
            'payment_details': notification_data.get('CARDNO')[-4:],  # epayco pads details with X's.
            'partner_id': self.partner_id.id,
            'provider_ref': notification_data['ALIAS'],
        })
        self.write({
            'token_id': token.id,
            'tokenize': False,
        })
        _logger.info(
            "created token with id %(token_id)s for partner with id %(partner_id)s from "
            "transaction with reference %(ref)s",
            {
                'token_id': token.id,
                'partner_id': self.partner_id.id,
                'ref': self.reference,
            },
        )

    def get_tax(self, table, name):
        try:
            sql = """select amount_tax from %s where name = '%s'
                            """ % (table, name)
            http.request.cr.execute(sql)
            result = http.request.cr.fetchall() or []
            amount_tax = 0
            tax = 0
            if result:
                (amount_tax) = result[0]
                if len(amount_tax) > 0:
                    for tax_amount in amount_tax:
                        tax = tax_amount
            return tax
        except KeyError as e:
            # Manejar errores por claves faltantes en los datos
            _logger.error("KeyError encountered in get tax info: %s", e)
            raise ValidationError(_("Invalid notification data: Missing key %s.") % str(e))

        except ValidationError as e:
            # Re-lanzar errores de validación con más contexto si es necesario
            _logger.warning("Validation error while get tax info: %s", e)
            raise e

        except Exception as e:
            # Capturar cualquier otra excepción inesperada
            _logger.exception("Unexpected error while get tax info.")
            raise UserError(_("An unexpected error occurred: %s") % str(e))
        

