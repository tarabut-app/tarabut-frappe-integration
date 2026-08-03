import importlib
from importlib import metadata

import frappe
from frappe.utils.caching import redis_cache

from tarabut_connector.api.auth import require_integration_user

SUPPORTED_DOCTYPES = (
    "Company",
    "Warehouse",
    "Cost Center",
    "Price List",
    "UOM",
    "Item",
    "Item Price",
    "Bin",
    "Customer",
    "Supplier",
    "Sales Order",
    "Purchase Order",
)


@frappe.whitelist()
def get_capabilities():
    """Return the connector and ERP versions used during capability negotiation."""
    require_integration_user()
    return {
        "connector": "tarabut_connector",
        "connector_version": _app_version("tarabut_connector"),
        "frappe_version": _app_version("frappe"),
        "erpnext_version": _app_version("erpnext"),
        "schema_version": "2",
        "roles": ["seller", "buyer"],
        "transports": ["direct"],
        "capabilities": {
            "delta_products": True,
            "webhooks": True,
            "push_sales_orders": True,
            "push_purchase_orders": True,
            "create_customers": True,
            "create_suppliers": True,
            "create_items": True,
        },
    }


def _app_version(app_name: str):
    for package_name in (app_name, app_name.replace("_", "-")):
        try:
            return metadata.version(package_name)
        except metadata.PackageNotFoundError:
            pass

    try:
        app = importlib.import_module(app_name)
        version = getattr(app, "__version__", None)
        if version:
            return version
    except ImportError:
        pass

    versions = getattr(frappe, "get_versions", dict)()
    if isinstance(versions, dict):
        app = versions.get(app_name, {})
        if isinstance(app, dict):
            return app.get("version") or "unknown"
    return "unknown"


@frappe.whitelist()
def configure_connection(connection_id: str, webhook_secret: str):
    """Store Tarabut's generated event credentials after authorization."""
    require_integration_user()
    if not connection_id or not webhook_secret or len(webhook_secret) < 16:
        frappe.throw("A valid Tarabut connection ID and webhook secret are required")
    settings = frappe.get_single("Tarabut Connector Settings")
    settings.tarabut_connection_id = connection_id
    settings.webhook_secret = webhook_secret
    settings.enabled = 1
    settings.save(ignore_permissions=True)
    return {"configured": True, "connection_id": connection_id}


@frappe.whitelist()
def get_connection_options(company: str | None = None):
    require_integration_user()
    _require_read_access()
    return _get_connection_options(company)


@redis_cache(ttl=300)
def _get_connection_options(company: str | None = None):
    companies = frappe.get_all(
        "Company", filters={"is_group": 0}, fields=["name", "default_currency"]
    )
    company_filter = {"company": company} if company else {}
    warehouses = frappe.get_all(
        "Warehouse",
        filters={**company_filter, "is_group": 0, "disabled": 0},
        fields=["name", "company"],
        order_by="name asc",
    )
    cost_centers = frappe.get_all(
        "Cost Center",
        filters={**company_filter, "is_group": 0, "disabled": 0},
        fields=["name", "company"],
        order_by="name asc",
    )
    price_lists = frappe.get_all(
        "Price List",
        filters={"selling": 1, "enabled": 1},
        fields=["name", "currency"],
        order_by="name asc",
    )
    uoms = frappe.get_all("UOM", fields=["name"], order_by="name asc")
    return {
        "companies": companies,
        "warehouses": warehouses,
        "cost_centers": cost_centers,
        "price_lists": price_lists,
        "uoms": uoms,
        "stock_formulas": ["actual_qty", "projected_qty", "available_qty"],
    }


def _require_read_access():
    for doctype in SUPPORTED_DOCTYPES:
        if frappe.has_permission(doctype, "read"):
            return
    frappe.throw(
        "The integration user cannot read ERPNext records", frappe.PermissionError
    )
