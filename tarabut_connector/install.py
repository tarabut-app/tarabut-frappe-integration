import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def after_install():
    create_roles()
    create_tarabut_custom_fields()


def after_migrate():
    """Backfill idempotent integration metadata after app upgrades."""
    create_roles()
    create_tarabut_custom_fields()


def create_roles():
    if not frappe.db.exists("Role", "Tarabut Integration User"):
        role = frappe.new_doc("Role")
        role.role_name = "Tarabut Integration User"
        role.desk_access = 1
        role.insert(ignore_permissions=True)


def create_tarabut_custom_fields():
    fields = {
        "Sales Order": [
            {
                "fieldname": "tarabut_section",
                "label": "Tarabut",
                "fieldtype": "Section Break",
                "insert_after": "source",
            },
            {
                "fieldname": "tarabut_order_set_id",
                "label": "Tarabut Order Set ID",
                "fieldtype": "Data",
                "insert_after": "tarabut_section",
                "read_only": 1,
            },
            {
                "fieldname": "tarabut_order_id",
                "label": "Tarabut Order ID",
                "fieldtype": "Data",
                "insert_after": "tarabut_order_set_id",
                "read_only": 1,
            },
            {
                "fieldname": "tarabut_sync_status",
                "label": "Tarabut Sync Status",
                "fieldtype": "Data",
                "insert_after": "tarabut_order_id",
                "read_only": 1,
            },
        ],
        "Purchase Order": [
            {
                "fieldname": "tarabut_section",
                "label": "Tarabut",
                "fieldtype": "Section Break",
                "insert_after": "supplier",
            },
            {
                "fieldname": "tarabut_order_set_id",
                "label": "Tarabut Order Set ID",
                "fieldtype": "Data",
                "insert_after": "tarabut_section",
                "read_only": 1,
            },
            {
                "fieldname": "tarabut_order_id",
                "label": "Tarabut Order ID",
                "fieldtype": "Data",
                "insert_after": "tarabut_order_set_id",
                "read_only": 1,
            },
            {
                "fieldname": "tarabut_sync_status",
                "label": "Tarabut Sync Status",
                "fieldtype": "Data",
                "insert_after": "tarabut_order_id",
                "read_only": 1,
            },
        ],
    }
    create_custom_fields(fields, update=True)
