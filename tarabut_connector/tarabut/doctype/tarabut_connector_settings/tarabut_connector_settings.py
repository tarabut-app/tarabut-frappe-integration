from urllib.parse import urlparse

import frappe
from frappe import _
from frappe.model.document import Document

DEFAULT_TARABUT_BASE_URL = "https://api.tarabut.app"
DEFAULT_TARABUT_WEBHOOK_URL = f"{DEFAULT_TARABUT_BASE_URL}/webhooks/erp/erpnext"


class TarabutConnectorSettings(Document):
    def before_validate(self):
        if not self.tarabut_base_url:
            self.tarabut_base_url = DEFAULT_TARABUT_BASE_URL
        if not self.tarabut_webhook_url:
            self.tarabut_webhook_url = DEFAULT_TARABUT_WEBHOOK_URL

    def validate(self):
        for label, value in (
            ("Tarabut Base URL", self.tarabut_base_url),
            ("Tarabut Webhook URL", self.tarabut_webhook_url),
        ):
            parsed = urlparse(value or "")
            if parsed.scheme != "https" or not parsed.hostname or parsed.username:
                frappe.throw(f"{label} must be a public HTTPS URL without credentials")
        if self.enabled and not self.tarabut_connection_id:
            frappe.throw(
                _("Tarabut Connection ID is required when Tarabut Connector is enabled")
            )
        if self.enabled and not self.get_password("webhook_secret"):
            frappe.throw(
                _("Webhook Secret is required when Tarabut Connector is enabled")
            )
