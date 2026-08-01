# Tarabut / ترابط

Installable Frappe/ERPNext integration app for Tarabut marketplace
synchronization.

Repository: `tarabut-frappe-integration`

Python/Frappe app module: `tarabut_connector`

The app exposes idempotent whitelisted methods used by Tarabut's Medusa ERP
module:

- `tarabut_connector.api.order.create_sales_order`
- `tarabut_connector.api.order.create_purchase_order`
- `tarabut_connector.api.order.find_document_by_idempotency_key`

It keeps ERPNext core upstream-compatible and adds Tarabut-specific fields
through Custom Fields during installation.

## Install

```bash
bench get-app https://github.com/tarabut-app/tarabut-frappe-integration
bench --site your-site install-app tarabut_connector
bench --site your-site migrate
```
