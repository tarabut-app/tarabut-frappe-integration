# Publishing on Frappe Cloud Marketplace

This is a maintainer checklist for publishing `tarabut_connector`. ERPNext users should follow the installation and connection instructions in the main README instead.

## Before submission

1. Keep the GitHub repository public under the Tarabut organization.
2. Confirm the release commit passes the ERPNext 15 and 16 GitHub Actions matrix.
3. Create a tagged GitHub release whose version matches `pyproject.toml` and `tarabut_connector/__init__.py`.
4. Use the packaged app icon at `tarabut_connector/public/images/tarabut-icon.png` for the listing logo.
5. Prepare current screenshots of the Tarabut Integration workspace, settings, mappings, and sync history, plus a short demo video.

Frappe requires Marketplace apps to be open source under a compatible license, hosted on GitHub, and backed by passing CI. The app is MIT licensed and its compatibility matrix is maintained in `.github/workflows/ci.yml`.

## Create the listing

1. Sign in to the Frappe Cloud dashboard as the Tarabut publisher account.
2. Open **Settings → Profile** and select **Become a Publisher** if the account is not already enabled.
3. Open **Marketplace**, select **+ Add App**, then **Add from GitHub**.
4. Authorize the Tarabut GitHub organization and select `tarabut-app/tarabut-frappe-integration`.
5. Select the supported Frappe versions and add the app to Marketplace. The initial listing remains a draft until Frappe approves it.

## Listing content

- **App name:** `tarabut_connector`
- **App title:** `Tarabut / ترابط`
- **Short description:** `Connect ERPNext catalogue and orders with Tarabut wholesale commerce`
- **Category:** E-commerce
- **Support URL:** <https://tarabut.app/support>
- **Privacy policy URL:** <https://tarabut.app/privacy>
- **Source URL:** <https://github.com/tarabut-app/tarabut-frappe-integration>

Write the long description for ERPNext users and describe the seller catalogue, draft Sales Order, buyer draft Purchase Order, mapping, retry, and audit features. Do not include Bench installation commands in the Marketplace long description because Frappe Cloud handles installation.

Upload a square logo of at least 200 by 200 pixels, screenshots in the Marketplace screenshot section, and the short demo video requested by the review guidelines.

## Publish a release

1. In the Marketplace app dashboard, create a release from the tested GitHub tag.
2. Select the compatible Frappe/ERPNext versions represented by the CI matrix.
3. Complete the release notes and submit the app and release for review.
4. Monitor the draft and release status in Frappe Cloud. If it remains in draft beyond the review window shown by Frappe, open a Frappe Cloud support ticket.

Current official instructions:

- [Publishing an app to Marketplace](https://docs.frappe.io/cloud/marketplace/publishing-an-app-to-marketplace)
- [Marketplace publishing guidelines](https://docs.frappe.io/cloud/marketplace/marketplace-guidelines)
- [App authoring guidelines](https://docs.frappe.io/cloud/marketplace/app-authoring-guidelines)
