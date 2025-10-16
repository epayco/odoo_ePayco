# Epayco Payment Acquirer v18.0

![Production/Stable](https://img.shields.io/badge/maturity-Production%2FStable-green.png)
[![License: AGPL-3](https://img.shields.io/badge/licence-AGPL--3-blue.png)](http://www.gnu.org/licenses/agpl-3.0-standalone.html)
[![GitHub Repository](https://img.shields.io/badge/github-epayco%2Fodoo_ePayco-lightgray.png?logo=github)](https://github.com/epayco/odoo_ePayco/tree/12.0/payment_epayco)

## Table of Contents

- [Installation](#installation)
- [Configuration](#configuration)
- [Bug Tracker](#bug-tracker)
- [Credits](#credits)

## Installation

To install this module, you need to:

1. Have access to the root directory where Odoo is installed.
2. Clone the repository or download the `.zip` file from [GitHub](https://github.com/epayco/odoo_ePayco/).
3. Extract the folder named `payment_epayco`.
4. Move the `payment_epayco` folder into the `server/odoo/addons` directory inside your Odoo root folder.
5. Restart Odoo services or update the database so that the module appears in the application list.
6. If the module does not appear, ensure that the CRM application is installed, as it is often required to activate the module.
7. Once the module appears in the application list, click "Install".

## Configuration

1. Go to **Website / Configuration / Payment Providers**.
2. Locate the **ePayco payment method** and click "Activate".
3. Under the **Credentials** tab, enter the values for `P_CUST_ID_CLIENTE`, `P_KEY`, `PUBLIC_KEY`, and `PRIVATE_KEY`. You can find these credentials in your ePayco dashboard under **Integrations / API Keys** in the **Secret Keys** section.
4. **Transaction Status Mapping**: By default, the module maps ePayco transaction statuses to Odoo transaction statuses. Ensure that this mapping aligns with your business logic, as the order processing in Odoo depends on transaction statuses. For more details, refer to the [Odoo Order Handling Documentation](https://www.odoo.com/documentation/18.0/en/applications/websites/ecommerce/ecommerce_management/order_handling.html). For information on ePayco transaction status codes, refer to the [Response Codes Documentation](https://docs.epayco.com/docs/paginas-de-respuestas).
5. Once you configure your credentials, click the **Publish** button. 
6. You can test the module in **Sandbox Mode** to simulate purchases and verify the transaction flow before switching to **Production Mode** for real payments.
7. To make the plugin available in the store, go to **Website > Configuration > Payment Methods**, click "Add", choose how you want the plugin name to be displayed, then select ePayco from the list of payment methods and save the changes.


### Important Note

Ensure that you configure the **Response and Confirmation URLs** in your ePayco dashboard under **Integrations / Customization / Response and Confirmation URLs**. The module automatically generates the following URLs:

- **Response URL:** `<base_url>/payment/epayco/response/`
- **Confirmation URL:** `<base_url>/payment/epayco/confirmation/`

## Bug Tracker

Report bugs on [GitHub Issues](https://github.com/epayco/odoo_ePayco/issues). Before opening a new issue, please check if it has already been reported.

If you find a new issue, help us by providing detailed feedback using [this link](https://github.com/epayco/odoo_ePayco/issues/new?body=module:%20payment_epayco%0Aversion:%2012.0%0A%0A**Steps%20to%20reproduce**%0A-%20...%0A%0A**Current%20behavior**%0A%0A**Expected%20behavior**).

Do not contact contributors directly for support or technical issues.

## Credits

### Authors

- **ePayco**

### Contributors

- Ricardo Saldarriaga (<ricardo.saldarriaga@payco.co>)

This module is part of the [epayco/odoo_ePayco](https://github.com/epayco/odoo_ePayco) project on GitHub.

We welcome contributions!
