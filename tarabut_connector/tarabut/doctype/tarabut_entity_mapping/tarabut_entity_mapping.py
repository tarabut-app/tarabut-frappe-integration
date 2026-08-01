import frappe
from frappe.model.document import Document


class TarabutEntityMapping(Document):
    def validate(self):
        duplicate = frappe.db.get_value(
            "Tarabut Entity Mapping",
            {
                "entity_type": self.entity_type,
                "tarabut_id": self.tarabut_id,
                "name": ("!=", self.name),
            },
            "name",
        )
        if duplicate:
            frappe.throw(
                f"Tarabut mapping already exists for {self.entity_type} {self.tarabut_id}"
            )
        reverse_duplicate = frappe.db.get_value(
            "Tarabut Entity Mapping",
            {
                "erp_doctype": self.erp_doctype,
                "erp_name": self.erp_name,
                "name": ("!=", self.name),
            },
            "name",
        )
        if reverse_duplicate:
            frappe.throw(
                f"ERPNext {self.erp_doctype} {self.erp_name} is already mapped to another Tarabut entity"
            )
