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
        await loadJS('https://epayco-checkout-testing.s3.us-east-1.amazonaws.com/checkout.preprod.js');
        if (epaycoSession && epaycoSession.data && epaycoSession.data.sessionId) {
            const handlerNew = ePayco.checkout.configure({
                sessionId: epaycoSession.data.sessionId,
                external: external
            });
            handlerNew.openNew();
        } else {
            // Fallback: abrir checkout tradicional si no hay sessionId
            const epaycoJS = ePayco.checkout.configure({
                key: processingValues['public_key'],
                test: processingValues['test']
            });
            epaycoJS.open(epaycoOptions.data);
        }
    },
    async _makeSession(epayco_token, data) {
        try {
            const headers = { 'Content-Type': 'application/json' };
            if (epayco_token) {
                headers['Authorization'] = `Bearer ${epayco_token}`;
            }
            const response = await fetch("https://eks-apify-service.epayco.io/payment/session/create", {
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
                "name": processingValues['reference'],
                "description": processingValues['reference'],
                "invoice": processingValues['reference'],
                "currency": processingValues['currency'],
                "amount": processingValues['amount'].toString(),
                "tax_base": processingValues['base_tax'].toString(),
                "tax": processingValues['tax'].toString(),
                "taxIco": "0",
                "country": "CO",
                "lang": processingValues['lang_checkout'],
                "external": processingValues['checkout_external'],
                "extra2": processingValues['extra2'],
                "extra3": processingValues['reference'],
                "confirmation": processingValues['notify_url'],
                "response": processingValues['return_url'],
                "name_billing": processingValues['firstname'],
                "email_billing": processingValues['email'],
                "autoclick": "true",
                "ip": myIp.ip,
                "test": processingValues['test'].toString(),
                "extras_epayco": {"extra5": "P32"},
                "checkout_version": 2
            }
        };
    },

});
