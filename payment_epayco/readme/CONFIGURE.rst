* Ir a Sitio web / Configuración / Comercio electrónico / Métodos de pago.
* Ir al método de pago ePayco y presionar el botón "Activar".
* En la tab de "Credenciales" colocar los datos correspondientes a los campos P_CUST_ID_CLIENTE, P_KEY y PUBLIC_KEY, los cuales los puede conseguir en su dashboard de ePayco en el menú de Integraciones / Llaves API en la seccion "LLaves secretas".

*En la tab "Configuración" establecer lo siguiente:*

* Diario de pago.
  
* Por defecto el método de pago estará disponible solo para usuarios que estén ubicados en Colombia, si este no es el caso déjelo abierto para todos los países en el campo "Países".  * Tipo de Checkout: Por defecto sera Onpage Checkout. Revisar en la documentación los dos posibles modos de checkout que ofrece ePayco https://docs.epayco.co/payments/checkout.
  
* Franquicias: por defecto el modulo carga las franquicias actuales que soporta ePayco pero si en algún momento cambia alguna de estas, se puede configurar en esta sección. Tomar en cuenta que el valor del campo código debe ser exactamente igual al código que tenga la franquicia en ePayco. Para mayor detalle mirar la tabla de franquicias en el siguiente link https://docs.epayco.co/payments/checkout.
  
* Estados de transacción: Por defecto el modulo hace una asociación entre los distintos estados de transacciones de ePayco y los estados de transacciones de Odoo. Revisar si este mapeo inicial se adapta a su lógica de negocio debido a que dependiendo del estado de la transacción Odoo manejara el flujo del pedido de venta, para mas detalle consultar: https://www.odoo.com/documentation/user/12.0/ecommerce/shopper_experience/payment_acquirer.html. Para mas detalles sobre los códigos de estados de transacción de ePayco mirar la tabla "Códigos de respuesta" en el siguiente link https://docs.epayco.co/payments/checkout.
  
* Tipos de documento: Al igual que con los estados de transacción esta es una asociación entre los tipos de documentos de ePayco y los tipos de documentos cargados por el modulo de la localización. Revisar los tipos de documentos de ePayco en la tabla "Tipos de documento" en el siguiente link https://docs.epayco.co/payments/checkout. Para mayor detalle sobre los tipos de documentos en Odoo mirar el siguiente link https://github.com/odoo/odoo/blob/1c3d51283edfbe9b7339690515189f2b06cc82dc/addons/l10n_co/models/res_partner.py#L9.

* Para hacer el método de pago disponible en el ecommerce, pulsar el botón Publicar.
  
* Si ya ha probado el modulo y esta conforme puede cambiar el ambiente a producción.

*Tomar en cuenta que en su dashboard de ePayco debe configurar las urls de respuesta y confirmación en el menú Integraciones en la sección "Opciones pasarela". El modulo genera automáticamente estas urls:*

* URL de respuesta: <base_url>/payment/epayco/response/
* URL de confirmacion: <base_url>/payment/epayco/confirmation/
