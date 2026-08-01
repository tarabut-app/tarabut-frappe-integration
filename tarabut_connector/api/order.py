import json
from typing import Any

import frappe
from frappe import _
from frappe.utils import nowdate


@frappe.whitelist()
def find_document_by_idempotency_key(key: str):
    record = frappe.db.get_value(
        "Tarabut Sync Record",
        {"idempotency_key": key},
        ["erp_doctype", "erp_name", "status"],
        as_dict=True,
    )
    if not record or not record.erp_doctype or not record.erp_name:
        return None
    return {
        "doctype": record.erp_doctype,
        "name": record.erp_name,
        "status": record.status,
    }


@frappe.whitelist()
def create_sales_order(idempotency_key: str, company: str, payload: Any):
    payload = _coerce_payload(payload)
    existing = find_document_by_idempotency_key(idempotency_key)
    if existing:
        return existing

    sync = _begin_sync(idempotency_key, "inbound", "sales_order", payload)
    try:
        order = payload.get("order") or {}
        doc = frappe.new_doc("Sales Order")
        doc.company = company
        doc.customer = _resolve_customer(order)
        doc.transaction_date = nowdate()
        doc.delivery_date = nowdate()
        doc.po_no = str(order.get("display_id") or order.get("id") or "")
        doc.tarabut_order_set_id = payload.get("order_set_id")
        doc.tarabut_order_id = order.get("id")
        doc.tarabut_sync_status = "Draft from Tarabut"
        _append_items(doc, order, "delivery_date")
        doc.insert(ignore_permissions=True)
        _complete_sync(sync, "Sales Order", doc.name)
        return {"doctype": "Sales Order", "name": doc.name}
    except Exception as exc:
        _fail_sync(sync, exc)
        raise


@frappe.whitelist()
def create_purchase_order(idempotency_key: str, company: str, payload: Any):
    payload = _coerce_payload(payload)
    existing = find_document_by_idempotency_key(idempotency_key)
    if existing:
        return existing

    sync = _begin_sync(idempotency_key, "inbound", "purchase_order", payload)
    try:
        order = payload.get("order") or {}
        seller = payload.get("seller") or {}
        doc = frappe.new_doc("Purchase Order")
        doc.company = company
        doc.supplier = _resolve_supplier(seller)
        doc.transaction_date = nowdate()
        doc.schedule_date = nowdate()
        doc.tarabut_order_set_id = payload.get("order_set_id")
        doc.tarabut_order_id = order.get("id")
        doc.tarabut_sync_status = "Draft from Tarabut"
        _append_items(doc, order, "schedule_date")
        doc.insert(ignore_permissions=True)
        _complete_sync(sync, "Purchase Order", doc.name)
        return {"doctype": "Purchase Order", "name": doc.name}
    except Exception as exc:
        _fail_sync(sync, exc)
        raise


def _coerce_payload(payload: Any) -> dict:
    if isinstance(payload, str):
        return json.loads(payload)
    if isinstance(payload, dict):
        return payload
    frappe.throw(_("Tarabut payload must be an object"))


def _begin_sync(idempotency_key: str, direction: str, entity_type: str, payload: dict):
    sync = frappe.new_doc("Tarabut Sync Record")
    sync.idempotency_key = idempotency_key
    sync.direction = direction
    sync.entity_type = entity_type
    sync.tarabut_id = (payload.get("order") or {}).get("id")
    sync.status = "Processing"
    sync.payload = json.dumps(payload, default=str)
    sync.insert(ignore_permissions=True)
    return sync


def _complete_sync(sync, doctype: str, name: str):
    sync.status = "Succeeded"
    sync.erp_doctype = doctype
    sync.erp_name = name
    sync.save(ignore_permissions=True)


def _fail_sync(sync, exc: Exception):
    sync.status = "Failed"
    sync.error = str(exc)
    sync.save(ignore_permissions=True)


def _append_items(doc, order: dict, schedule_field: str):
    items = order.get("items") or []
    if not items:
        frappe.throw(_("Tarabut order has no items"))

    for item in items:
        item_code = _resolve_item_code(item)
        row = {
            "item_code": item_code,
            "qty": item.get("quantity") or 1,
            "rate": _resolve_rate(item),
            schedule_field: nowdate(),
        }
        doc.append("items", row)


def _resolve_item_code(item: dict) -> str:
    metadata = item.get("metadata") or {}
    candidates = [
        metadata.get("erp_item_code"),
        item.get("variant_sku"),
        item.get("sku"),
        item.get("product_title"),
        item.get("title"),
    ]
    item_code = next((value for value in candidates if value), None)
    if not item_code:
        frappe.throw(_("Tarabut item is missing an ERP item mapping"))

    if not frappe.db.exists("Item", item_code):
        settings = _settings()
        if not settings.allow_create_items:
            frappe.throw(_("ERPNext Item does not exist: {0}").format(item_code))
        doc = frappe.new_doc("Item")
        doc.item_code = item_code
        doc.item_name = item.get("product_title") or item.get("title") or item_code
        doc.item_group = settings.default_item_group or "All Item Groups"
        doc.stock_uom = settings.default_uom or "Nos"
        doc.insert(ignore_permissions=True)

    return item_code


def _resolve_rate(item: dict) -> float:
    for key in ("unit_price", "unit_total", "subtotal", "total"):
        value = item.get(key)
        if value is not None:
            return float(value)
    return 0


def _resolve_customer(order: dict) -> str:
    email = order.get("email")
    customer_name = email or order.get("customer_id") or order.get("id")
    if not customer_name:
        frappe.throw(_("Tarabut order is missing customer identity"))

    if not frappe.db.exists("Customer", customer_name):
        settings = _settings()
        if not settings.allow_create_parties:
            frappe.throw(_("ERPNext Customer does not exist: {0}").format(customer_name))
        doc = frappe.new_doc("Customer")
        doc.customer_name = customer_name
        doc.customer_type = "Company"
        doc.insert(ignore_permissions=True)
    return customer_name


def _resolve_supplier(seller: dict) -> str:
    supplier_name = seller.get("name") or seller.get("id")
    if not supplier_name:
        frappe.throw(_("Tarabut seller is missing supplier identity"))

    if not frappe.db.exists("Supplier", supplier_name):
        settings = _settings()
        if not settings.allow_create_parties:
            frappe.throw(_("ERPNext Supplier does not exist: {0}").format(supplier_name))
        doc = frappe.new_doc("Supplier")
        doc.supplier_name = supplier_name
        doc.supplier_type = "Company"
        doc.insert(ignore_permissions=True)
    return supplier_name


def _settings():
    return frappe.get_single("Tarabut Connector Settings")
