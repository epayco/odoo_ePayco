odoo.define('payment_payco.paycowidget', function (require) {
    'use strict';
    var widgetRegistry = require('web.widget_registry');
    var Widget = require('web.Widget');
    var utils = require('web.utils');
    var core = require('web.core');
    var PaycoWidget = Widget.extend({
        template: 'payment_payco.payco_button',
        xmlDependencies: ['/payment_payco/static/src/xml/paycowidget.xml'],
        events: {
        'click .btn-primary': '_onClick'
        },
        init: function (parent, data, options) {
            this._super.apply(this, arguments);
            this.text = options.attrs.title || options.attrs.text;
            this.className = 'btn btn-primary';
            this.res_model = options.attrs.res_model || 'account.move';
        },
        willStart: function () {
            return Promise.all([
                this._super.apply(this, arguments),
            ]);
        },
        _prefill: function(){
            
        },
        _onClick: async function(){
        
            utils.set_cookie('payco_reload_url', window.location.href);
            var self = this;
            var invoce_id = this.__parentedParent.state.data.id;
            const datas = await this._rpc({
                model: 'account.move',
                method: 'get_invoice_details',
                args: [invoce_id],
            });
            return this._rpc({
                route: '/payco/payment/transaction/'+String(invoce_id),
                params: datas,
            }).then(processingValues => {
                processingValues['is_backend_pay'] = true;
                self.pay_by_payco(processingValues);
            });
        },
        pay_by_payco: function(processingValues){
        
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

                });
            return;
        }
    });

    widgetRegistry.add('payco_button', PaycoWidget);

    return PaycoWidget;
});
