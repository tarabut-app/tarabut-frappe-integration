# Tarabut / ترابط for ERPNext

[Tarabut](https://tarabut.app) is an Iraqi wholesale commerce platform that connects traders with suppliers and factories for product discovery, ordering, payment, delivery, and order tracking.

This app connects an ERPNext company to Tarabut. It is for businesses that sell through Tarabut, buy through Tarabut, or do both.

## What the integration does

For a seller, the integration can:

- read selected ERPNext `Item`, `Item Price`, UOM, Warehouse, and `Bin` data;
- import catalogue, selling prices, and warehouse availability into Tarabut for review;
- keep approved catalogue mappings synchronized after ERPNext changes;
- create one draft ERPNext `Sales Order` for each Tarabut seller order;
- show the ERPNext document and its current status in the Tarabut seller panel.

For a buyer, the integration can:

- create one draft ERPNext `Purchase Order` per supplier for a Tarabut order set;
- map Tarabut sellers to ERPNext Suppliers and purchased variants to ERPNext Items;
- preserve the agreed Tarabut quantities, prices, discounts, shipping, and order references.

Repeated requests use the same idempotency key, so a retry returns the original ERPNext document instead of creating a duplicate. The app also keeps mapping and sync-history records in the **Tarabut Integration** workspace.

The first release creates draft orders only. It does not submit orders or create invoices, payments, delivery notes, purchase receipts, or stock entries.

## Supported versions

- Frappe Framework 15 or 16
- ERPNext 15 or 16

Tarabut checks the installed Frappe, ERPNext, and connector versions during authorization and rejects unsupported major versions.

## Installation

Run these commands from your Bench directory:

```bash
git clone https://github.com/tarabut-app/tarabut-frappe-integration apps/tarabut_connector
./env/bin/pip install --editable apps/tarabut_connector
grep -qxF tarabut_connector sites/apps.txt || printf '\ntarabut_connector\n' >> sites/apps.txt
bench --site your-site.example install-app tarabut_connector
bench --site your-site.example migrate
```

The `apps/tarabut_connector` destination is required because the public repository name and the Frappe app name are intentionally different. Replace `your-site.example` with your ERPNext site name.

## Connect ERPNext to Tarabut

### Recommended: one-click connection

1. In ERPNext, search for and open **Tarabut Connector Settings** as a System Manager.
2. Click **Connect with Tarabut**.
3. Sign in to the Tarabut seller panel if needed, select the ERPNext Company, and approve the connection.
4. Select the selling Price List, stock formula, ERPNext Warehouses, and the corresponding Tarabut stock location for every selected Warehouse.
5. Save the settings and run the first full catalogue sync. Review the proposed changes before committing them.

The button creates an expiring, single-use pairing code. After approval, the app provisions a dedicated ERPNext user with only the **Tarabut Integration User** role and sends its newly generated API credentials directly to Tarabut. The credentials are never included in the browser URL. Tarabut stores them encrypted and installs the webhook signing secret automatically.

### Advanced manual connection

If one-click pairing cannot be used, open **Advanced manual setup** on the Tarabut integration page. You can enter API credentials for a dedicated user with the **Tarabut Integration User** role, or use an ERPNext OAuth Client with the production redirect URI `https://api.tarabut.app/vendor/erp/oauth/callback`.

## ERPNext settings and workspace

After installation, search ERPNext Desk for **Tarabut Integration**. The workspace provides:

- **Tarabut Settings** for connection state and creation policies;
- **Tarabut Mappings** for Item, Customer, and Supplier exceptions;
- **Tarabut Sync History** for completed and failed inbound or outbound work.

The Tarabut connection ID and webhook secret are installed automatically after successful authorization. They identify the ERPNext connection and sign ERPNext-to-Tarabut event notifications. They should not be copied between sites.

The creation policies are:

- **Allow Creating Missing Items** — permits a reviewed Tarabut item to be created when no mapped ERPNext Item exists. It is disabled by default.
- **Allow Creating Customers and Suppliers** — permits automatic missing-party creation outside the seller's explicit order-review action. It is disabled by default; a seller can still approve creating a specific Customer from the Tarabut order sync workspace.
- **Default Item Group** and **Default UOM** — used only when creation of a missing Item is explicitly allowed.

Production Tarabut endpoints are preconfigured. Endpoint overrides are under the **Advanced** tab for staging or Tarabut-supported private deployments.

## Catalogue and stock rules

- The seller chooses one selling Price List and one explicit stock formula.
- Every selected ERPNext Warehouse must map to a Tarabut stock location.
- `actual_qty`, `projected_qty`, and calculated available quantity are different policies; Tarabut never changes between them silently.
- Item/UOM is the sellable identity. Warehouse changes inventory placement, not product identity.
- Each Item/UOM becomes one Tarabut product with one default variant. Alternate UOMs are separate products, not variants of one product.
- Products for the same ERPNext Item share one stock pool. Each UOM consumes the shared stock using its ERPNext conversion factor, so pack products do not duplicate inventory.
- Disabled Items and changed mappings are presented for review rather than deleted automatically.
- `Bin` is ERPNext's per-Item, per-Warehouse stock record. The integration reads its quantities to update the mapped Tarabut stock location.

## Order behavior

- Seller orders become draft `Sales Order` documents.
- Buyer order sets become one draft `Purchase Order` per seller child order.
- Tarabut order and order-set IDs are stored on the ERPNext document.
- A timeout after document creation is treated as an unknown result. Tarabut looks up the idempotency key before retrying.
- ERPNext status is mirrored for visibility only; changing or cancelling an ERPNext order does not automatically change the Tarabut order.

## Security

- Use a dedicated restricted ERPNext integration user.
- Expose ERPNext only over valid public HTTPS for direct mode.
- Keep OAuth secrets, API secrets, and webhook secrets out of logs and support messages.
- Tarabut event notifications are signed with HMAC and include a timestamp and unique event ID. Expired signatures are rejected, and duplicate event IDs are recorded without processing the event again.
- Private or LAN-only ERPNext sites are not supported by direct mode; contact Tarabut before enabling a private-site transport.

## Support

Visit [tarabut.app](https://tarabut.app) to learn about Tarabut. For connector problems, open an issue in the [Tarabut Frappe integration repository](https://github.com/tarabut-app/tarabut-frappe-integration/issues).

## License

MIT
