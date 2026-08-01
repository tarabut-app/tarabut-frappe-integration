import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

LEGACY_WORKSPACE_TITLE = "Tarabut / ترابط"


def after_install():
    create_roles()
    create_integration_permissions()
    create_tarabut_custom_fields()


def after_migrate():
    """Backfill idempotent integration metadata after app upgrades."""
    create_roles()
    create_integration_permissions()
    create_tarabut_custom_fields()
    repair_workspace_metadata()


def repair_workspace_metadata():
    """Repair the route-breaking title retained by existing Workspace records."""
    if not frappe.db.exists("Workspace", "Tarabut"):
        return

    workspace = frappe.get_doc("Workspace", "Tarabut")
    changed = False

    if workspace.title == LEGACY_WORKSPACE_TITLE:
        workspace.title = "Tarabut"
        changed = True

    if workspace.label == LEGACY_WORKSPACE_TITLE:
        workspace.label = "Tarabut"
        changed = True

    if workspace.content and LEGACY_WORKSPACE_TITLE in workspace.content:
        workspace.content = workspace.content.replace(LEGACY_WORKSPACE_TITLE, "Tarabut")
        changed = True

    if changed:
        workspace.save(ignore_permissions=True)
        frappe.clear_cache()


def before_uninstall():
    """Do not silently destroy connector audit and mapping history."""
    sync_count = frappe.db.count("Tarabut Sync Record")
    mapping_count = frappe.db.count("Tarabut Entity Mapping")
    if sync_count or mapping_count:
        frappe.throw(
            "Tarabut Connector has sync or mapping history. Disable the connector "
            "instead of uninstalling it, or export and explicitly remove that history first."
        )


def create_roles():
    if not frappe.db.exists("Role", "Tarabut Integration User"):
        role = frappe.new_doc("Role")
        role.role_name = "Tarabut Integration User"
        role.desk_access = 1
        role.insert(ignore_permissions=True)


def create_integration_permissions():
    from frappe.permissions import add_permission, update_permission_property

    read_doctypes = [
        "Company",
        "Warehouse",
        "Cost Center",
        "Price List",
        "UOM",
        "Item Price",
        "Bin",
        "Item",
        "Customer",
        "Supplier",
        "Sales Order",
        "Purchase Order",
    ]
    for doctype in read_doctypes:
        if not frappe.db.exists("DocType", doctype):
            continue
        permission_filters = {
            "parent": doctype,
            "role": "Tarabut Integration User",
            "permlevel": 0,
        }
        if not frappe.db.exists("Custom DocPerm", permission_filters):
            add_permission(doctype, "Tarabut Integration User", 0)
        update_permission_property(doctype, "Tarabut Integration User", 0, "read", 1)
        for property_name in ("create", "write", "delete", "submit", "cancel"):
            update_permission_property(
                doctype, "Tarabut Integration User", 0, property_name, 0
            )


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
                "fieldname": "tarabut_buyer_id",
                "label": "Tarabut Buyer ID",
                "fieldtype": "Data",
                "insert_after": "tarabut_order_id",
                "read_only": 1,
            },
            {
                "fieldname": "tarabut_sync_status",
                "label": "Tarabut Sync Status",
                "fieldtype": "Data",
                "insert_after": "tarabut_buyer_id",
                "read_only": 1,
            },
            {
                "fieldname": "tarabut_order_total",
                "label": "Tarabut Order Total",
                "fieldtype": "Currency",
                "options": "currency",
                "insert_after": "tarabut_sync_status",
                "read_only": 1,
            },
            {
                "fieldname": "tarabut_shipping_total",
                "label": "Tarabut Shipping Total",
                "fieldtype": "Currency",
                "options": "currency",
                "insert_after": "tarabut_order_total",
                "read_only": 1,
            },
            {
                "fieldname": "tarabut_discount_total",
                "label": "Tarabut Discount Total",
                "fieldtype": "Currency",
                "options": "currency",
                "insert_after": "tarabut_shipping_total",
                "read_only": 1,
            },
            {
                "fieldname": "tarabut_tax_total",
                "label": "Tarabut Tax Total",
                "fieldtype": "Currency",
                "options": "currency",
                "insert_after": "tarabut_discount_total",
                "read_only": 1,
            },
            {
                "fieldname": "tarabut_idempotency_key",
                "label": "Tarabut Idempotency Key",
                "fieldtype": "Data",
                "insert_after": "tarabut_tax_total",
                "read_only": 1,
                "unique": 1,
                "hidden": 1,
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
                "fieldname": "tarabut_seller_id",
                "label": "Tarabut Seller ID",
                "fieldtype": "Data",
                "insert_after": "tarabut_order_id",
                "read_only": 1,
            },
            {
                "fieldname": "tarabut_sync_status",
                "label": "Tarabut Sync Status",
                "fieldtype": "Data",
                "insert_after": "tarabut_seller_id",
                "read_only": 1,
            },
            {
                "fieldname": "tarabut_order_total",
                "label": "Tarabut Order Total",
                "fieldtype": "Currency",
                "options": "currency",
                "insert_after": "tarabut_sync_status",
                "read_only": 1,
            },
            {
                "fieldname": "tarabut_shipping_total",
                "label": "Tarabut Shipping Total",
                "fieldtype": "Currency",
                "options": "currency",
                "insert_after": "tarabut_order_total",
                "read_only": 1,
            },
            {
                "fieldname": "tarabut_discount_total",
                "label": "Tarabut Discount Total",
                "fieldtype": "Currency",
                "options": "currency",
                "insert_after": "tarabut_shipping_total",
                "read_only": 1,
            },
            {
                "fieldname": "tarabut_tax_total",
                "label": "Tarabut Tax Total",
                "fieldtype": "Currency",
                "options": "currency",
                "insert_after": "tarabut_discount_total",
                "read_only": 1,
            },
            {
                "fieldname": "tarabut_idempotency_key",
                "label": "Tarabut Idempotency Key",
                "fieldtype": "Data",
                "insert_after": "tarabut_tax_total",
                "read_only": 1,
                "unique": 1,
                "hidden": 1,
            },
        ],
    }
    create_custom_fields(fields, update=True)
