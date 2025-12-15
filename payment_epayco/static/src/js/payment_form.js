/** @odoo-module **/
/* global ePayco */

import { _t } from "@web/core/l10n/translation";
import { loadJS } from "@web/core/assets";
import paymentForm from '@payment/js/payment_form';

paymentForm.include({

    // #=== DOM MANIPULATION ===#

    /**
     * Update the payment context to set the flow to 'direct'.
     *
     * @override method from @payment/js/payment_form
     * @private
     * @param {number} providerId - The id of the selected payment option's provider.
     * @param {string} providerCode - The code of the selected payment option's provider.
     * @param {number} paymentOptionId - The id of the selected payment option
     * @param {string} paymentMethodCode - The code of the selected payment method, if any.
     * @param {string} flow - The online payment flow of the selected payment option.
     * @return {void}
     */
    async _prepareInlineForm(providerId, providerCode, paymentOptionId, paymentMethodCode, flow) {
        if (providerCode !== 'epayco') {
            this._super(...arguments);
            return;
        }

        if (flow === 'token') {
            return; // No need to update the flow for tokens.
        }

        // Overwrite the flow of the select payment method.
        this._setPaymentFlow('direct');
    },

    // #=== PAYMENT FLOW ===#

    async _processDirectFlow(providerCode, paymentOptionId, paymentMethodCode, processingValues) {
        if (providerCode !== 'epayco') {
            this._super(...arguments);
            return;
        }
        let myIp = await this._getIp();
        // Obtener el token JWT desde los valores de procesamiento
        const epayco_token = processingValues['epayco_token'];
        const epaycoOptions = this._prepareEpaycoOptions(processingValues, myIp);
        let epaycoSession = await this._makeSession(epayco_token, epaycoOptions.data);
        let external = epaycoOptions.data.external == 'true' ? true : false;
        await loadJS('https://checkout.epayco.co/checkout-v2.js');
        if (epaycoSession && epaycoSession.success && epaycoSession.data && epaycoSession.data.sessionId) {
            const checkout = ePayco.checkout.configure({
                sessionId: epaycoSession.data.sessionId,
                type: external ? "standard" : "onepage",
                test: epaycoOptions.data.test
            });
            
            // Event handlers
            checkout.onCreated(() => {
                console.log("Evento cuando se crea el flujo transaccional");
            });

            checkout.onErrors(errors => {
                console.log("Evento que notifica un error en la integración");
                console.error(errors);
            });

            checkout.onClosed(() => {
                console.log("Evento que notifica cuando se cierra el checkout");
            });
            
            checkout.open();
        } else {
            console.error("Error: No se pudo obtener sessionId", epaycoSession);
        }
    },
    async _makeSession(epayco_token, data) {
        try {
            const headers = { 'Content-Type': 'application/json' };
            if (epayco_token) {
                headers['Authorization'] = `Bearer ${epayco_token}`;
            }
            const response = await fetch("https://apify.epayco.co/payment/session/create", {
                method: 'POST',
                headers: headers,
                body: JSON.stringify(data),
            });
            if (!response.ok) {
                throw new Error(`Error en la solicitud: ${response.status}`);
            }
            const result = await response.json();
            return result;
        } catch (error) {
            console.error('Error al realizar el fetch:', error);
        }
    },
    async _getIp(){
    try {
            const response = await fetch("https://api.ipify.org?format=json", {
                method: 'GET'
            });
            if (!response.ok) {
                throw new Error(`Error en la solicitud: ${response.status}`);
            }
            const result = await response.json();
            return result;
        } catch (error) {
            console.error('Error al realizar el fetch:', error);
        }
    },

    /**
     * Prepare the options to init the ePayco Object.
     *
     * @param {object} processingValues - The processing values.
     * @return {object}
     */
    _prepareEpaycoOptions(processingValues, myIp) {
        return {
            'data': {
                "checkout_version": "2",
                "name": processingValues['reference'].substring(0, 50),
                "description": processingValues['reference'].substring(0, 50),
                "invoice": processingValues['reference'],
                "currency": processingValues['currency'].toLowerCase(),
                "amount": parseFloat(processingValues['amount']),
                "taxBase": parseFloat(processingValues['base_tax']),
                "tax": parseFloat(processingValues['tax']),
                "taxIco": parseFloat(0),
                "country": processingValues['country'],
                "lang": processingValues['lang_checkout'],
                "confirmation": processingValues['notify_url'],
                "response": processingValues['return_url'],
                "billing": {
                    "name": processingValues['firstname'],
                    "address": processingValues['address'] || "",
                    "email": processingValues['email'],
                    "country": processingValues['country'],
                },
                "autoclick": true,
                "ip": myIp.ip,
                "test": processingValues['test'].toString() === "true",
                "extras": {
                    "extra2": processingValues['extra2'],
                    "extra3": processingValues['reference']
                },
                "extrasEpayco": {
                    "extra5": "P34"
                },
                "methodsDisable": [],
                "dues": 1,
                "noRedirectOnClose": true,
                "forceResponse": false,
                "uniqueTransactionPerBill": false,
                "config": {},
                "method": "POST",
              
                "autoClick": false,
                "external": processingValues['checkout_external']
            }
        };
    },

});
