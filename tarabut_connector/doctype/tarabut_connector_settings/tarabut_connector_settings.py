import frappe
from frappe.model.document import Document


class TarabutConnectorSettings(Document):
    def validate(self):
        if self.enabled and not self.get_password("webhook_secret"):
            frappe.throw("Webhook Secret is required when Tarabut Connector is enabled")
