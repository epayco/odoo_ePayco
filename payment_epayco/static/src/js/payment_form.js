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
        const epaycoOptions = this._prepareEpaycoOptions(processingValues);
        await loadJS('https://checkout.epayco.co/checkout.js');
        console.log(epaycoOptions);
        const epaycoJS = ePayco.checkout.configure({
            key: epaycoOptions.public_key,
            test: epaycoOptions.test
        });
        epaycoJS.open(epaycoOptions.data);
    },

    /**
     * Prepare the options to init the ePayco Object.
     *
     * @param {object} processingValues - The processing values.
     * @return {object}
     */
    _prepareEpaycoOptions(processingValues) {
        return Object.assign({}, {
            'data': {
                "name": processingValues['reference'],
                "description": processingValues['reference'],
                "invoice": processingValues['reference'],
                "currency": processingValues['currency'],
                "amount": processingValues['amount'].toString(),
                "tax_base": processingValues['base_tax'].toString(),
                "tax": processingValues['tax'].toString(),
                "taxIco": "0".toString(),
                "country": processingValues['country'],
                "lang": processingValues['lang_checkout'],
                "external": processingValues['checkout_external'],
                "extra2": processingValues['extra2'],
                "extra3": processingValues['reference'],
                "confirmation": processingValues['confirmation_url'],
                "response": processingValues['response_url'],
                "name_billing": processingValues['first_name'],
                "email_billing": processingValues['email'],
                "mobilephone_billing":  processingValues['cellphone'],
                "address_billing": processingValues['address'],
                "extras_epayco": {"extra5":"P32"},
                "test": processingValues['test'].toString(),
                "autoclick": "true",
                "ip": processingValues['ip']
            },
            'public_key': processingValues['public_key'],
            'private_key': processingValues['private_key'],
            'test': processingValues['test'].toString()
        });
    },

});