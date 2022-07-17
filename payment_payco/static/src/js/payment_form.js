odoo.define('payment_payco.payment_form', require => {
    'use strict';

    const core = require('web.core');
    const ajax = require('web.ajax');

    const checkoutForm = require('payment.checkout_form');
    const manageForm = require('payment.manage_form');

    const _t = core._t;

    const PaycoMixin = {
        _processRedirectPayment: function (provider, paymentOptionId, processingValues) {
            
            if (provider !== 'payco') {
                return this._super(...arguments);
            }
            var self = this;
            $.post('/payment/payco/transction/process', processingValues).done(function(data, status ){
            try{
                var myObj = JSON.parse(data);
                var jsondata = JSON.parse(myObj);
                var handler = ePayco.checkout.configure({
                    key: jsondata.public_key,
                    test: jsondata.test
                });
                var dataHandler={
                  //Parametros compra (obligatorio)
                  name: jsondata.txnid,
                  description: jsondata.txnid,
                  invoice: jsondata.txnid,
                  currency: jsondata.currency,
                  amount: jsondata.amount,
                  tax_base: jsondata.base_tax,
                  tax: jsondata.tax,
                  country: jsondata.country,
                  lang: jsondata.lang,
                  //Onpage="false" - Standard="true"
                  external: jsondata.checkoutType,
                  //Atributos opcionales
                  extra1: jsondata.extra1,
                  extra2: jsondata.productinfo,
                  extra3: jsondata.txnid,
                  confirmation: jsondata.confirmation_url,
                  response: jsondata.response_url,
                  //Atributos cliente
                  name_billing: jsondata.first_name,
                  email_billing: jsondata.email,
                  phone_billing: jsondata.phone_number
              };
              handler.open(dataHandler)
            }catch (e) {
              console.log("epayco error")
            }
            }).fail(function(xhr, status, error) {

            })
            return ;
        },
    };
    try{
    checkoutForm.include(PaycoMixin);
    manageForm.include(PaycoMixin);
    }catch (e) {
              console.log("epayco error")
            }
});