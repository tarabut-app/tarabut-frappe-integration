# Tarabut / ترابط ERPNext Integration

[Tarabut](https://tarabut.app) is a wholesale commerce platform in Iraq. It connects traders with suppliers, factories, products, ordering, payment, delivery, and order tracking.

This Frappe app lets an ERPNext site exchange order and catalog-related updates with Tarabut. It is intended for companies that use ERPNext and also sell or buy through Tarabut.

## What this app provides

The app adds the ERPNext-side integration needed for Tarabut order sync.

It can:

- Receive order sync requests from Tarabut.
- Create ERPNext `Sales Order` documents for buyer/customer-side orders.
- Create ERPNext `Purchase Order` documents for seller/supplier-side orders.
- Track each sync request with an idempotency key so repeated requests do not create duplicate ERPNext documents.
- Store sync payloads, linked ERPNext documents, status, and error details.
- Store mappings between Tarabut entities and ERPNext documents.
- Add Tarabut reference fields to ERPNext Sales Orders and Purchase Orders.
- Notify Tarabut when selected ERPNext orders, item prices, or `Bin` records change.

## Who should install it

Install this app if:

- You use ERPNext v15.
- Your business needs to connect ERPNext with Tarabut.
- You want Tarabut orders to appear inside ERPNext.
- You want ERPNext changes such as order, item, price, or `Bin` updates to notify Tarabut.

You do not need this app just to browse or use Tarabut as a regular trader from the Tarabut app.

## Supported ERPNext documents

The current version works with:

- `Sales Order`
- `Purchase Order`
- `Item`
- `Item Price`
- `Bin`
- `Customer`
- `Supplier`

`Sales Order` and `Purchase Order` are created from inbound Tarabut sync requests.

`Item`, `Item Price`, and `Bin` changes can be sent back to Tarabut through webhook notifications.

## Requirements

- Frappe Framework v15 or later.
- ERPNext v15 or later.
- Bench access to your ERPNext site.
- Tarabut integration credentials.

## Installation

From your Bench directory:

```bash
bench get-app https://github.com/tarabut-app/tarabut-frappe-integration
bench --site your-site.example install-app tarabut_connector
bench --site your-site.example migrate
```

Replace `your-site.example` with your ERPNext site name.

## Setup in ERPNext

After installation, open ERPNext Desk and search for:

```text
Tarabut Connector Settings
```

Configure:

- `Enabled`
- `Tarabut Connection ID`
- `Webhook Secret`
- `Default Item Group`
- `Default UOM`
- `Allow Creating Missing Items`
- `Allow Creating Customers and Suppliers`

Recommended production settings:

- Use the production URL defaults unless Tarabut support asks you to change them.
- Keep `Allow Creating Missing Items` disabled unless your Tarabut products already have clean ERPNext item codes or SKUs.
- Use a dedicated ERPNext API user for Tarabut.
- Store the webhook secret securely.
- Use HTTPS for ERPNext and Tarabut endpoints.

`Tarabut Connection ID` and `Webhook Secret` are provided during Tarabut integration onboarding.

`Tarabut Connection ID` tells Tarabut which ERPNext connection is sending or receiving data.

`Webhook Secret` is used to sign ERPNext-to-Tarabut webhook messages, so Tarabut can verify that the message came from the configured ERPNext site.

The app uses Tarabut production endpoints by default. Advanced URL settings are reserved for Tarabut support, staging, or private deployment scenarios.

## What is created in ERPNext

The app creates these Tarabut records:

- `Tarabut Connector Settings`
- `Tarabut Sync Record`
- `Tarabut Entity Mapping`

It also creates:

- `Tarabut Integration User` role
- Tarabut fields on `Sales Order`
- Tarabut fields on `Purchase Order`

The Tarabut fields added to Sales Orders and Purchase Orders are:

- `Tarabut Order Set ID`
- `Tarabut Order ID`
- `Tarabut Sync Status`

These fields help ERPNext users trace a document back to its Tarabut order.

## Integration methods

Tarabut calls ERPNext through Frappe whitelisted methods.

### Check an existing sync request

```text
tarabut_connector.api.order.find_document_by_idempotency_key
```

Use this to check whether a Tarabut request was already processed.

### Create a Sales Order

```text
tarabut_connector.api.order.create_sales_order
```

Creates an ERPNext `Sales Order`.

Required arguments:

- `idempotency_key`
- `company`
- `payload`

### Create a Purchase Order

```text
tarabut_connector.api.order.create_purchase_order
```

Creates an ERPNext `Purchase Order`.

Required arguments:

- `idempotency_key`
- `company`
- `payload`

## Outbound webhook to Tarabut

When the integration is enabled, the app listens for updates on:

- `Sales Order`
- `Purchase Order`
- `Item`
- `Item Price`
- `Bin`

When one of these ERPNext records changes, the app sends a webhook to Tarabut.

Example payload:

```json
{
  "connection_id": "your-connection-id",
  "event_id": "uuid",
  "doctype": "Sales Order",
  "name": "SO-0001",
  "modified_at": "2026-08-01 12:00:00.000000"
}
```

Each webhook request includes:

```text
X-Tarabut-Signature: sha256=<signature>
```

Tarabut should verify this signature using the shared webhook secret.

## How items, customers, and suppliers are matched

For Items, the app checks the incoming Tarabut payload in this order:

1. `metadata.erp_item_code`
2. `variant_sku`
3. `sku`
4. `product_title`
5. `title`

For Customers, the app checks:

1. Order email.
2. Tarabut customer ID.
3. Tarabut order ID.

For Suppliers, the app checks:

1. Seller name.
2. Seller ID.

Missing Items, Customers, and Suppliers are created only if the related setting allows it.

## Current limitations

The current version creates draft ERPNext orders only.

It does not yet create:

- Sales Invoices
- Purchase Invoices
- Payment Entries
- Delivery Notes
- Purchase Receipts
- Stock Entries

It also does not submit ERPNext documents automatically. ERPNext users should review and submit created documents according to their normal accounting and inventory workflow.

## Support

For Tarabut information, visit [tarabut.app](https://tarabut.app).

For integration issues, open an issue in this repository:

```text
https://github.com/tarabut-app/tarabut-frappe-integration/issues
```

## License

MIT.
