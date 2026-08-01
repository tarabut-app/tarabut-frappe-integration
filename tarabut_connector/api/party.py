from typing import Any

import frappe

from tarabut_connector.api.auth import require_integration_user
from tarabut_connector.api.order import _coerce_payload, _settings


@frappe.whitelist()
def upsert_customer(tarabut_id: str, payload: Any):
    require_integration_user()
    data = _coerce_payload(payload)
    return _upsert_party("Customer", "customer", tarabut_id, data)


@frappe.whitelist()
def upsert_supplier(tarabut_id: str, payload: Any):
    require_integration_user()
    data = _coerce_payload(payload)
    return _upsert_party("Supplier", "supplier", tarabut_id, data)


@frappe.whitelist()
def upsert_item(tarabut_id: str, payload: Any):
    require_integration_user()
    settings = _settings()
    if not settings.allow_create_items:
        frappe.throw("Creating Items through Tarabut is disabled")
    data = _coerce_payload(payload)
    mapping = _mapping("item", tarabut_id)
    item_code = mapping.erp_name if mapping else data.get("item_code")
    if not item_code:
        frappe.throw("item_code is required")

    if frappe.db.exists("Item", item_code):
        doc = frappe.get_doc("Item", item_code)
    else:
        doc = frappe.new_doc("Item")
        doc.item_code = item_code
        doc.item_group = data.get("item_group") or settings.default_item_group
        doc.stock_uom = data.get("stock_uom") or settings.default_uom
    doc.item_name = data.get("item_name") or item_code
    doc.description = data.get("description") or doc.description
    doc.save(ignore_permissions=True)
    _save_mapping("item", tarabut_id, "Item", doc.name)
    return {"doctype": "Item", "name": doc.name}


def _upsert_party(doctype, entity_type, tarabut_id, data):
    settings = _settings()
    if not settings.allow_create_parties:
        frappe.throw("Creating Customers and Suppliers through Tarabut is disabled")
    mapping = _mapping(entity_type, tarabut_id)
    party_name = mapping.erp_name if mapping else data.get("name")
    if party_name and frappe.db.exists(doctype, party_name):
        doc = frappe.get_doc(doctype, party_name)
    else:
        doc = frappe.new_doc(doctype)
        display_name = data.get("display_name") or data.get("name") or tarabut_id
        if doctype == "Customer":
            doc.customer_name = display_name
            doc.customer_type = data.get("customer_type") or "Company"
        else:
            doc.supplier_name = display_name
            doc.supplier_type = data.get("supplier_type") or "Company"
    doc.save(ignore_permissions=True)
    _save_mapping(entity_type, tarabut_id, doctype, doc.name)
    return {"doctype": doctype, "name": doc.name}


def _mapping(entity_type, tarabut_id):
    name = frappe.db.get_value(
        "Tarabut Entity Mapping",
        {"entity_type": entity_type, "tarabut_id": tarabut_id, "status": "Active"},
        "name",
    )
    return frappe.get_doc("Tarabut Entity Mapping", name) if name else None


def _save_mapping(entity_type, tarabut_id, erp_doctype, erp_name):
    mapping = _mapping(entity_type, tarabut_id) or frappe.new_doc(
        "Tarabut Entity Mapping"
    )
    mapping.entity_type = entity_type
    mapping.tarabut_id = tarabut_id
    mapping.erp_doctype = erp_doctype
    mapping.erp_name = erp_name
    mapping.status = "Active"
    mapping.save(ignore_permissions=True)
