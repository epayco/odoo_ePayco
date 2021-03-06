=======================
Epayco Payment Acquirer
=======================

.. !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
   !! This file is generated by oca-gen-addon-readme !!
   !! changes will be overwritten.                   !!
   !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

.. |badge1| image:: https://img.shields.io/badge/maturity-Production%2FStable-green.png
    :target: https://odoo-community.org/page/development-status
    :alt: Production/Stable
.. |badge2| image:: https://img.shields.io/badge/licence-AGPL--3-blue.png
    :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
    :alt: License: AGPL-3
.. |badge3| image:: https://img.shields.io/badge/github-epayco%2Fodoo_ePayco-lightgray.png?logo=github
    :target: https://github.com/epayco/odoo_ePayco/tree/12.0/payment_epayco
    :alt: epayco/odoo_ePayco

|badge1| |badge2| |badge3| 

Epayco Payment Acquirer.

**Table of contents**

.. contents::
   :local:

Installation
============

Para instalar este modulo necesita:

1. Agregar el directorio clonado de este repositorio a la ruta de addons de la instancia de Odoo. 
2. Ir a la base de datos y actualizar la lista de aplicaciones.
3. Instalar el modulo payment_epayco.
   

Configuration
=============

* Ir a Sitio web / Configuración / Comercio electrónico / Métodos de pago.
* Ir al método de pago ePayco y presionar el botón "Activar".
* En la tab de "Credenciales" colocar los datos correspondientes a los campos P_CUST_ID_CLIENTE, P_KEY y PUBLIC_KEY, los cuales los puede conseguir en su dashboard de ePayco en el menú de Integraciones / Llaves API en la seccion "LLaves secretas".

* Estados de transacción: Por defecto el modulo hace una asociación entre los distintos estados de transacciones de ePayco y los estados de transacciones de Odoo. Revisar si este mapeo inicial se adapta a su lógica de negocio debido a que dependiendo del estado de la transacción Odoo manejara el flujo del pedido de venta, para mas detalle consultar: https://www.odoo.com/documentation/user/12.0/ecommerce/shopper_experience/payment_acquirer.html. Para mas detalles sobre los códigos de estados de transacción de ePayco mirar la tabla "Códigos de respuesta" en el siguiente link https://docs.epayco.co/payments/checkout.

* Para hacer el método de pago disponible en el ecommerce, pulsar el botón Publicar.
  
* Si ya ha probado el modulo y esta conforme puede cambiar el ambiente a producción.

*Tomar en cuenta que en su dashboard de ePayco debe configurar las urls de respuesta y confirmación en el menú Integraciones en la sección "Opciones pasarela". El modulo genera automáticamente estas urls:*

* URL de respuesta: <base_url>/payment/epayco/response/
* URL de confirmacion: <base_url>/payment/epayco/confirmation/

Bug Tracker
===========

Bugs are tracked on `GitHub Issues <https://github.com/epayco/odoo_ePayco/issues>`_.
In case of trouble, please check there if your issue has already been reported.
If you spotted it first, help us smashing it by providing a detailed and welcomed
`feedback <https://github.com/epayco/odoo_ePayco/issues/new?body=module:%20payment_epayco%0Aversion:%2012.0%0A%0A**Steps%20to%20reproduce**%0A-%20...%0A%0A**Current%20behavior**%0A%0A**Expected%20behavior**>`_.

Do not contact contributors directly about support or help with technical issues.

Credits
=======

Authors
~~~~~~~

* ePayco

Contributors
~~~~~~~~~~~~

* Ricardo Saldarriaga <ricardo.saldarriaga@payco.co>

Other credits
~~~~~~~~~~~~~

Maintainers
~~~~~~~~~~~

.. |maintainer-mamcode| image:: https://github.com/mamcode.png?size=40px
    :target: https://github.com/mamcode
    :alt: mamcode

Current maintainer:

|maintainer-mamcode| 

This module is part of the `epayco/odoo_ePayco <https://github.com/epayco/odoo_ePayco/tree/12.0/payment_epayco>`_ project on GitHub.

You are welcome to contribute.
