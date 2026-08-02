# Changelog

## 0.3.2 - 2026-08-02

- Prefer an explicit `tarabut_public_site_url` site config value for pairing links when ERPNext runs behind an origin-only tunnel host.

## 0.3.1 - 2026-08-02

- Use the public forwarded ERPNext host when creating one-click pairing links behind tunnels or reverse proxies.

## 0.3.0 - 2026-08-02

- Add a one-click connection flow initiated by a System Manager from ERPNext.
- Use an expiring, single-use pairing code to associate the ERPNext site with an authenticated Tarabut seller.
- Provision and rotate a dedicated restricted integration user's API credentials automatically without exposing them in the browser URL.
- Move endpoint overrides and the hidden webhook secret into the Advanced tab.
- Keep OAuth and manually generated API credentials as recovery options in Tarabut.

## 0.2.1 - 2026-08-02

- Present connection state as system-managed status and direct disconnected users to Tarabut's seller panel.
- Keep platform-installed credentials hidden while showing the assigned connection ID after authorization.
- Allow disconnected sites to save advanced Tarabut API and webhook URL overrides.
- Hide creation defaults until the integration is connected.

## 0.2.0 - 2026-08-01

- Add ERPNext 15 and 16 compatibility checks and CI coverage.
- Add OAuth/API-token connection setup with automatically installed webhook credentials.
- Add catalogue, price, UOM, Warehouse, Bin, and Cost Center discovery APIs.
- Add idempotent draft Sales Order and Purchase Order creation.
- Add reviewed Item, Customer, and Supplier mappings with safe opt-in creation policies.
- Add signed, coalesced ERPNext change notifications with retry history.
- Add the Tarabut Integration workspace, audit records, order references, and checkout totals.

## 0.1.2 - 2026-08-01

- Improve ERPNext installation and connection documentation.

## 0.1.1 - 2026-08-01

- Use the packaged Tarabut app icon.

## 0.1.0 - 2026-08-01

- Initial standalone Frappe app scaffold.
