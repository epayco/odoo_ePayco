# -*- coding: utf-8 -*-
# Copyright 2019 ePayco.co
# - Manuel Marquez <buzondemam@gmail.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from lxml import objectify
from werkzeug import urls

from odoo.addons.payment.tests.common import PaymentAcquirerCommon
from odoo.addons.payment_epayco.controllers.main import EpaycoController


class EpaycoCommon(PaymentAcquirerCommon):

    def setUp(self):
        super(EpaycoCommon, self).setUp()
        self.epayco = self.env.ref('payment_epayco.payment_acquirer_epayco')
        self.currency_cop = self.env.ref('base.COP')
        self.country_co = self.env.ref('base.co')
        self.buyer_values.update({
            'partner_lang': 'es_CO',
            'partner_country': self.country_co,
            'partner_country_id': self.country_co.id,
            'partner_country_name': self.country_co.name,
            'billing_partner_lang': 'es_CO',
            'billing_partner_country': self.country_co,
            'billing_partner_country_id': self.country_co.id,
            'billing_partner_country_name': self.country_co.name,
        })
        self.buyer.write({
            'country_id': self.country_co.id,
            'l10n_co_document_type': 'national_citizen_id',
            'vat': '123456789',
        })


class EpaycoTest(EpaycoCommon):

    def test_10_epayco_form_render(self):
        """Check button form rendering."""

        self.epayco.write({
            'epayco_p_cust_id': '45767',
            'epayco_p_key': '2cd2b59d9b3f76989d7f14d9c0671ce9ab50c6a4',
            'epayco_public_key': 'cb3c56b60ac95b76c2f015e3005b4617',
        })
        self.assertEqual(
            self.epayco.environment, 'test', 'test without test environment')

        # ----------------------------------------
        # Test: button direct rendering
        # ----------------------------------------
        res = self.epayco.render(
            'SO400', 320.0,
            self.currency_cop.id,
            partner_id=self.buyer_id,
            values=self.buyer_values)
        tree = objectify.fromstring(res)

        data_set = tree.xpath("//input[@name='data_set']")
        self.assertEqual(
            len(data_set), 1,
            'ePayco: Found %d "data_set" input instead of 1' % len(data_set))

        self.assertEqual(
            data_set[0].get('data-action-url'),
            '/payment/epayco/checkout/',
            'ePayco: wrong form POST url')
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        lang = 'es' if 'es' in self.buyer.lang else 'en'
        epayco_document_type = self.env['epayco.document.type']

        buyer_document_type = epayco_document_type.search([(
            'l10n_co_document_type',
            '=',
            self.buyer.l10n_co_document_type)])[0].epayco_document_type

        form_values = {
            'currency_code': 'cop',
            'epayco_public_key': 'cb3c56b60ac95b76c2f015e3005b4617',
            'amount': '320.0',
            'country_code': 'co',
            'epayco_checkout_external': 'false',
            'epayco_env_test': 'true',
            'epayco_lang': lang,
            'response_url': urls.url_join(
                base_url, EpaycoController._response_url),
            'confirmation_url': urls.url_join(
                base_url, EpaycoController._confirmation_url),
            'billing_partner_email': self.buyer.email,
            'billing_partner_name': self.buyer.name,
            'billing_partner_address': self.buyer_values.get(
                'billing_partner_address'),
            'billing_partner_document_type': buyer_document_type,
            'billing_partner_phone': self.buyer_values.get(
                'billing_partner_phone'),
            'billing_partner_vat': self.buyer.vat,
            'reference': 'SO400',
        }

        for form_input in tree.input:
            if form_input.get('name') in ['submit', 'data_set']:
                continue
            self.assertEqual(
                form_input.get('value'),
                form_values[form_input.get('name')],
                'ePayco: wrong value for input %s: received %s instead of %s'
                % (form_input.get('name'), form_input.get('value'),
                   form_values[form_input.get('name')])
            )
