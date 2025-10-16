-- disable payumoney payment provider
UPDATE payment_provider
   SET epayco_cust_id = NULL,
       epayco_public_key = NULL,
       epayco_private_key = NULL,
       epayco_p_key = NULL,
       epayco_checkout_type = 'onpage',
       epayco_checkout_lang = 'es';
