# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import hashlib

import requests

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.payment_epayco import const


_logger = logging.getLogger(__name__)


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('epayco', "Epayco")], ondelete={'epayco': 'set default'})
    epayco_cust_id = fields.Char(
        string="P_CUST_ID_CLIENTE", help="",
        required_if_provider='epayco')
    epayco_public_key = fields.Char(
        string="PUBLIC_KEY",
        required_if_provider='epayco', groups='base.group_system')
    epayco_private_key = fields.Char(
        string="PRIVATE_KEY", required_if_provider='epayco', groups='base.group_system')
    epayco_p_key = fields.Char(
        string="P_KEY", required_if_provider='epayco', groups='base.group_system')
    epayco_checkout_type = fields.Selection(
        [('onpage', 'Onpage Checkout'), ('standard', 'Standard Checkout')],
        string="Checkout", required_if_provider='epayco',
    )
    epayco_checkout_lang = fields.Selection(
        [('en', 'English'), ('es', 'Español')],
        string="lenguage", required_if_provider='epayco',
    )

    #=== COMPUTE METHODS ===#

    def _compute_feature_support_fields(self):
        """ Override of `payment` to enable additional features. """
        super()._compute_feature_support_fields()
        self.filtered(lambda p: p.code == 'epayco').update({
            'support_tokenization': True,
        })

    #=== BUSINESS METHODS ===#
    
    def _epayco_generate_signature(self, values, incoming=True):
        if incoming:
            p_key = self.epayco_p_key
            x_ref_payco = values.get('x_ref_payco')
            x_transaction_id = values.get('x_transaction_id')
            x_amount = values.get('x_amount')
            x_currency_code = values.get('x_currency_code')
            hash_str_bytes = bytes('%s^%s^%s^%s^%s^%s' % (
                self.epayco_cust_id,
                p_key,
                x_ref_payco,
                x_transaction_id,
                x_amount,
                x_currency_code), 'utf-8')
            hash_object = hashlib.sha256(hash_str_bytes)
            hash = hash_object.hexdigest()
        return hash    

    @api.model
    def _get_compatible_providers(self, *args, is_validation=False, **kwargs):
        """ Override of payment to unlist epayco providers for validation operations. """
        providers = super()._get_compatible_providers(*args, is_validation=is_validation, **kwargs)

        if is_validation:
            providers = providers.filtered(lambda p: p.code != 'epayco')

        return providers

    def _get_supported_currencies(self):
        """ Override of `payment` to return the supported currencies. """
        supported_currencies = super()._get_supported_currencies()
        if self.code == 'epayco':
            supported_currencies = supported_currencies.filtered(
                lambda c: c.name in const.SUPPORTED_CURRENCIES
            )
        return supported_currencies

    def _get_default_payment_method_codes(self):
        """ Override of `payment` to return the default payment method codes. """
        default_codes = super()._get_default_payment_method_codes()
        if self.code != 'epayco':
            return default_codes
        return const.DEFAULT_PAYMENT_METHODS_CODES

    def get_epayco_token(self):
        """
        Obtiene el token JWT de ePayco usando las credenciales configuradas en el proveedor.
        Retorna el token como string, o None si falla.
        """
        # SDK-1360: endpoint distinto en Test Mode -- las llaves de prueba de
        # este ecosistema no funcionan contra el endpoint de produccion (ver
        # nota en const.py).
        url = const.EPAYCO_LOGIN_URL_TEST if self.state == 'test' else const.EPAYCO_LOGIN_URL_PROD
        public_key = self.epayco_public_key
        private_key = self.epayco_private_key
        headers = {'Content-Type': 'application/json'}
        try:
            resp = requests.post(
                url,
                headers=headers,
                json={},
                auth=requests.auth.HTTPBasicAuth(public_key, private_key),
                timeout=15
            )
        except requests.RequestException as e:
            _logger.error(f"Error en la llamada a ePayco API: {e}")
            return None
        if resp.status_code != 200:
            _logger.error(f"Respuesta no OK: {resp.status_code} - {resp.text}")
            return None
        data = resp.json()
        return data.get('token')

    def _epayco_create_checkout_session(self, session_data):
        """
        Crea una sesion de checkout de ePayco (`POST .../payment/session/create`)
        desde el backend, en vez de que el navegador del comprador la cree
        directamente con el JWT expuesto en el DOM.

        Antes de esto, `EpaycoController.epayco_checkout` obtenia el token
        (`get_epayco_token`, arriba) solo para pasarlo sin cifrar al
        cliente en un input hidden -- visible para cualquiera que
        inspeccionara el codigo fuente de la pagina, y suficiente por si
        solo para llamar a la API de ePayco en nombre del comercio. Ahora
        el token nunca sale del servidor: este metodo lo obtiene, arma el
        header `Authorization: Bearer`, crea la sesion, y solo devuelve el
        `sessionId` resultante -- ese si es seguro de exponer al cliente,
        es un identificador de una sola sesion de checkout ya creada, no
        una credencial reusable.

        :param dict session_data: el mismo payload que antes armaba el JS
            del template `payment_epayco.proccess` (`checkout_version`,
            `name`, `description`, `invoice`, `currency`, `amount`,
            `taxBase`, `tax`, `taxIco`, `country`, `lang`, `confirmation`,
            `response`, `billing`, `autoclick`, `ip`, `test`, `extras`,
            `extrasEpayco`, `method`, `autoClick`, `methodsDisable`,
            `dues`, `noRedirectOnClose`, `forceResponse`,
            `uniqueTransactionPerBill`, `config`).
        :return: el `sessionId` de la sesion creada, o `None` si fallo.
        :rtype: str | None
        """
        token = self.get_epayco_token()
        if not token:
            _logger.error(
                "epayco: no se pudo obtener el token JWT; no se puede "
                "crear la sesion de checkout."
            )
            return None

        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer %s' % token,
        }
        try:
            response = requests.post(
                const.EPAYCO_SESSION_CREATE_URL_TEST if self.state == 'test' else const.EPAYCO_SESSION_CREATE_URL_PROD,
                json=session_data,
                headers=headers,
                timeout=15,
            )
        except requests.RequestException as e:
            _logger.error("epayco: error creando sesion de checkout: %s", e)
            return None
        if response.status_code != 200:
            _logger.error(
                "epayco: respuesta no OK creando sesion de checkout: %s - %s",
                response.status_code, response.text,
            )
            return None

        resp_data = response.json() or {}
        session = resp_data.get('data') or {}
        session_id = session.get('sessionId')
        if not resp_data.get('success') or not session_id:
            _logger.error(
                "epayco: respuesta invalida creando sesion de checkout: %s",
                resp_data,
            )
            return None
        return session_id

    def _epayco_get_transaction_status(self, ref_epayco):
        """
        Consulta a ePayco el estado real de una transaccion por su
        referencia propia (`ref_payco`/`x_ref_payco`), reusando el mismo
        endpoint publico que ya usa el controlador de respuesta/confirmacion
        (`controllers/main.py`, `EpaycoController._epayco_process_response`)
        para validar el redirect sincrono del comprador.

        Es el unico endpoint de "consulta de estado" verificado en este
        ecosistema que acepta el `ref_payco` propio de ePayco en vez de
        la referencia del comercio (por eso el cron de reconciliacion,
        SDK-1360, `payment.transaction._cron_epayco_sync_pending_transactions`,
        solo puede reconciliar transacciones para las que ya se
        persistio `provider_reference`, ver
        `PaymentTransaction._get_tx_from_notification_data`). En eso
        coincide con `Charge::transaction($uid)` de epayco-php (`GET
        /transaction/response.json?ref_payco=`) -- pero NO es el mismo
        contrato exacto: ese llamado de epayco-php manda ademas
        `public_key` en el querystring, mientras que este endpoint no
        manda ninguna credencial. Es decir, esta consulta NO esta
        "scoped" al comercio -- cualquiera que conozca/adivine un
        `ref_payco` valido podria consultarlo. Sigue siendo seguro
        porque quien llama a este metodo (el redirect, el webhook, y el
        cron via `_epayco_process_notification_data`) siempre valida
        despues la firma (`EpaycoController._verify_notification_signature`)
        antes de aplicar cualquier dato que venga de aqui -- esa
        verificacion de firma NO es redundante, es la unica cosa que
        efectivamente ata la respuesta al comercio/transaccion
        correctos.

        :param str ref_epayco: la referencia de ePayco (`x_ref_payco`) de
            la transaccion a consultar.
        :return: el dict `data` de la respuesta de ePayco (mismas claves
            `x_...` que trae cualquier notificacion/webhook), o `None` si
            la consulta fallo o no devolvio datos.
        :rtype: dict | None
        """
        url = (
            const.EPAYCO_VALIDATION_URL_TEST if self.state == 'test'
            else const.EPAYCO_VALIDATION_URL_PROD
        ) % (ref_epayco,)
        try:
            response = requests.get(url, timeout=15)
        except requests.RequestException as e:
            _logger.error(
                "epayco: error querying transaction status for ref_payco %s: %s",
                ref_epayco, e,
            )
            return None
        if response.status_code != 200:
            _logger.warning(
                "epayco: non-200 response (%s) querying transaction status for ref_payco %s",
                response.status_code, ref_epayco,
            )
            return None
        return response.json().get('data')
