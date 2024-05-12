-- disable ogone payment provider
UPDATE payment_provider
   SET epayco_pspid = NULL,
       epayco_userid = NULL,
       epayco_password = NULL,
       epayco_shakey_in = NULL,
       epayco_shakey_out = NULL;
