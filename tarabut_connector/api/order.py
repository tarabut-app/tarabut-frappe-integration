import json
from typing import Any

import frappe
from frappe import _
from frappe.exceptions import DuplicateEntryError, UniqueValidationError
from frappe.utils import nowdate

from tarabut_connector.api.auth import require_integration_user


@frappe.whitelist()
def find_document_by_idempotency_key(key: str):
    require_integration_user()
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
    require_integration_user()
    payload = _coerce_payload(payload)
    _validate_company(company)
    sync, existing = _reserve_sync(idempotency_key, "inbound", "sales_order", payload)
    if existing:
        return existing
    frappe.db.savepoint("tarabut_sales_order")
    try:
        order = payload.get("order") or {}
        doc = frappe.new_doc("Sales Order")
        doc.company = company
        doc.currency = order.get("currency_code") or doc.currency
        doc.customer = _resolve_customer(order)
        doc.transaction_date = nowdate()
        doc.delivery_date = nowdate()
        doc.po_no = str(order.get("display_id") or order.get("id") or "")
        doc.tarabut_order_set_id = payload.get("order_set_id")
        doc.tarabut_order_id = order.get("id")
        doc.tarabut_buyer_id = order.get("customer_id")
        doc.tarabut_sync_status = "Draft from Tarabut"
        doc.tarabut_idempotency_key = idempotency_key
        _set_tarabut_totals(doc, order)
        _append_items(doc, order, "delivery_date")
        doc.insert(ignore_permissions=True)
        _complete_sync(sync, "Sales Order", doc.name)
        return {"doctype": "Sales Order", "name": doc.name}
    except Exception as exc:
        frappe.db.rollback(save_point="tarabut_sales_order")
        _fail_sync(sync, exc)
        frappe.db.commit()
        raise


@frappe.whitelist()
def create_purchase_order(idempotency_key: str, company: str, payload: Any):
    require_integration_user()
    payload = _coerce_payload(payload)
    _validate_company(company)
    sync, existing = _reserve_sync(
        idempotency_key, "inbound", "purchase_order", payload
    )
    if existing:
        return existing
    frappe.db.savepoint("tarabut_purchase_order")
    try:
        order = payload.get("order") or {}
        seller = payload.get("seller") or {}
        doc = frappe.new_doc("Purchase Order")
        doc.company = company
        doc.currency = order.get("currency_code") or doc.currency
        doc.supplier = _resolve_supplier(seller)
        doc.transaction_date = nowdate()
        doc.schedule_date = nowdate()
        doc.tarabut_order_set_id = payload.get("order_set_id")
        doc.tarabut_order_id = order.get("id")
        doc.tarabut_seller_id = seller.get("id")
        doc.tarabut_sync_status = "Draft from Tarabut"
        doc.tarabut_idempotency_key = idempotency_key
        _set_tarabut_totals(doc, order)
        row_defaults = _purchase_order_row_defaults(
            company, payload.get("erp_settings") or {}
        )
        _append_items(doc, order, "schedule_date", row_defaults)
        doc.insert(ignore_permissions=True)
        _complete_sync(sync, "Purchase Order", doc.name)
        return {"doctype": "Purchase Order", "name": doc.name}
    except Exception as exc:
        frappe.db.rollback(save_point="tarabut_purchase_order")
        _fail_sync(sync, exc)
        frappe.db.commit()
        raise


def _coerce_payload(payload: Any) -> dict:
    if isinstance(payload, str):
        return json.loads(payload)
    if isinstance(payload, dict):
        return payload
    frappe.throw(_("Tarabut payload must be an object"))


def _reserve_sync(
    idempotency_key: str, direction: str, entity_type: str, payload: dict
):
    existing = find_document_by_idempotency_key(idempotency_key)
    if existing:
        return None, existing
    sync = frappe.new_doc("Tarabut Sync Record")
    sync.idempotency_key = idempotency_key
    sync.direction = direction
    sync.entity_type = entity_type
    sync.tarabut_id = (payload.get("order") or {}).get("id")
    sync.status = "Processing"
    sync.payload = json.dumps(payload, default=str)
    try:
        sync.insert(ignore_permissions=True)
        return sync, None
    except (DuplicateEntryError, UniqueValidationError):
        name = frappe.db.get_value(
            "Tarabut Sync Record", {"idempotency_key": idempotency_key}, "name"
        )
        if not name:
            raise
        sync = frappe.get_doc("Tarabut Sync Record", name)
        if sync.erp_doctype and sync.erp_name:
            return sync, {
                "doctype": sync.erp_doctype,
                "name": sync.erp_name,
                "status": sync.status,
            }
        if sync.status == "Processing":
            frappe.throw(
                "This Tarabut request is already being processed. Retry shortly."
            )
        sync.status = "Processing"
        sync.error = None
        sync.save(ignore_permissions=True)
        return sync, None


def _complete_sync(sync, doctype: str, name: str):
    sync.status = "Succeeded"
    sync.erp_doctype = doctype
    sync.erp_name = name
    sync.save(ignore_permissions=True)


def _fail_sync(sync, exc: Exception):
    sync.status = "Failed"
    sync.error = str(exc)
    sync.save(ignore_permissions=True)


def _append_items(
    doc, order: dict, schedule_field: str, row_defaults: dict | None = None
):
    items = order.get("items") or []
    if not items:
        frappe.throw(_("Tarabut order has no items"))

    for item in items:
        item_code = _resolve_item_code(item)
        row = {
            **(row_defaults or {}),
            "item_code": item_code,
            "qty": item.get("quantity") or 1,
            "rate": _resolve_rate(item),
            schedule_field: nowdate(),
        }
        uom = _resolve_uom(item, item_code)
        if uom:
            row["uom"] = uom
            row["conversion_factor"] = _conversion_factor(item_code, uom)
        doc.append("items", row)


def _set_tarabut_totals(doc, order: dict):
    doc.tarabut_order_total = order.get("total")
    doc.tarabut_shipping_total = order.get("shipping_total")
    doc.tarabut_discount_total = order.get("discount_total")
    doc.tarabut_tax_total = order.get("tax_total")


def _purchase_order_row_defaults(company: str, settings: dict) -> dict:
    if not isinstance(settings, dict):
        frappe.throw("ERP connection settings must be an object")
    defaults = {}
    target_warehouse = settings.get("target_warehouse") or settings.get(
        "default_target_warehouse"
    )
    if target_warehouse:
        warehouse_company = frappe.db.get_value(
            "Warehouse", target_warehouse, "company"
        )
        if warehouse_company != company:
            frappe.throw(
                f"Target Warehouse {target_warehouse} does not belong to {company}"
            )
        defaults["warehouse"] = target_warehouse
    cost_center = settings.get("cost_center") or settings.get("buying_cost_center")
    if cost_center:
        cost_center_company = frappe.db.get_value("Cost Center", cost_center, "company")
        if cost_center_company != company:
            frappe.throw(f"Cost Center {cost_center} does not belong to {company}")
        defaults["cost_center"] = cost_center
    return defaults


def _resolve_uom(item: dict, item_code: str) -> str | None:
    metadata = item.get("metadata") or {}
    uom = metadata.get("erpnext_uom") or metadata.get("erp_uom")
    if not uom:
        options = item.get("variant", {}).get("options") or []
        uom = next(
            (
                option.get("value")
                for option in options
                if str(option.get("option", {}).get("title", "")).lower() == "uom"
            ),
            None,
        )
    if not uom:
        return None
    stock_uom = frappe.db.get_value("Item", item_code, "stock_uom")
    if uom != stock_uom and not frappe.db.exists(
        "UOM Conversion Detail", {"parent": item_code, "uom": uom}
    ):
        frappe.throw(f"UOM {uom} is not configured for ERPNext Item {item_code}")
    return uom


def _conversion_factor(item_code: str, uom: str) -> float:
    stock_uom = frappe.db.get_value("Item", item_code, "stock_uom")
    if uom == stock_uom:
        return 1
    return float(
        frappe.db.get_value(
            "UOM Conversion Detail",
            {"parent": item_code, "uom": uom},
            "conversion_factor",
        )
        or 1
    )


def _resolve_item_code(item: dict) -> str:
    tarabut_id = item.get("variant_id") or item.get("id")
    if tarabut_id:
        mapped = frappe.db.get_value(
            "Tarabut Entity Mapping",
            {"entity_type": "item", "tarabut_id": tarabut_id, "status": "Active"},
            "erp_name",
        )
        if mapped:
            return mapped
    metadata = item.get("metadata") or {}
    explicit_item_code = metadata.get("erpnext_item_code") or metadata.get(
        "erp_item_code"
    )
    if explicit_item_code:
        if not frappe.db.exists("Item", explicit_item_code):
            frappe.throw(f"Mapped ERPNext Item does not exist: {explicit_item_code}")
        if tarabut_id:
            _save_local_mapping("item", tarabut_id, "Item", explicit_item_code)
        return explicit_item_code

    settings = _settings()
    if not settings.allow_create_items:
        frappe.throw("Tarabut item is missing a reviewed ERPNext Item mapping")
    item_code = item.get("variant_sku") or item.get("sku")
    if not item_code:
        frappe.throw("Tarabut item has no SKU to create an ERPNext Item")
    if not frappe.db.exists("Item", item_code):
        doc = frappe.new_doc("Item")
        doc.item_code = item_code
        doc.item_name = item.get("product_title") or item.get("title") or item_code
        doc.item_group = settings.default_item_group or "All Item Groups"
        doc.stock_uom = settings.default_uom or "Nos"
        doc.insert(ignore_permissions=True)
    if tarabut_id:
        _save_local_mapping("item", tarabut_id, "Item", item_code)
    return item_code


def _resolve_rate(item: dict) -> float:
    for key in ("unit_price", "unit_total", "subtotal", "total"):
        value = item.get(key)
        if value is not None:
            return float(value)
    return 0


def _resolve_customer(order: dict) -> str:
    if order.get("erp_customer"):
        if not frappe.db.exists("Customer", order["erp_customer"]):
            frappe.throw(f"ERPNext Customer does not exist: {order['erp_customer']}")
        if order.get("customer_id"):
            _save_local_mapping(
                "customer", order["customer_id"], "Customer", order["erp_customer"]
            )
        return order["erp_customer"]
    tarabut_id = order.get("customer_id")
    if tarabut_id:
        mapped = frappe.db.get_value(
            "Tarabut Entity Mapping",
            {
                "entity_type": "customer",
                "tarabut_id": tarabut_id,
                "status": "Active",
            },
            "erp_name",
        )
        if mapped:
            return mapped
    settings = _settings()
    if not settings.allow_create_parties:
        frappe.throw("Tarabut buyer is missing a reviewed ERPNext Customer mapping")
    email = order.get("email")
    customer_name = email or order.get("customer_id") or order.get("id")
    if not customer_name:
        frappe.throw(_("Tarabut order is missing customer identity"))

    existing_name = frappe.db.get_value(
        "Customer", {"customer_name": customer_name}, "name"
    )
    if not existing_name:
        doc = frappe.new_doc("Customer")
        doc.customer_name = customer_name
        doc.customer_type = "Company"
        doc.insert(ignore_permissions=True)
        existing_name = doc.name
    if tarabut_id:
        _save_local_mapping("customer", tarabut_id, "Customer", existing_name)
    return existing_name


def _resolve_supplier(seller: dict) -> str:
    if seller.get("erp_supplier"):
        if not frappe.db.exists("Supplier", seller["erp_supplier"]):
            frappe.throw(f"ERPNext Supplier does not exist: {seller['erp_supplier']}")
        if seller.get("id"):
            _save_local_mapping(
                "supplier", seller["id"], "Supplier", seller["erp_supplier"]
            )
        return seller["erp_supplier"]
    tarabut_id = seller.get("id")
    if tarabut_id:
        mapped = frappe.db.get_value(
            "Tarabut Entity Mapping",
            {
                "entity_type": "supplier",
                "tarabut_id": tarabut_id,
                "status": "Active",
            },
            "erp_name",
        )
        if mapped:
            return mapped
    settings = _settings()
    if not settings.allow_create_parties:
        frappe.throw("Tarabut seller is missing a reviewed ERPNext Supplier mapping")
    supplier_name = seller.get("name") or seller.get("id")
    if not supplier_name:
        frappe.throw(_("Tarabut seller is missing supplier identity"))

    existing_name = frappe.db.get_value(
        "Supplier", {"supplier_name": supplier_name}, "name"
    )
    if not existing_name:
        doc = frappe.new_doc("Supplier")
        doc.supplier_name = supplier_name
        doc.supplier_type = "Company"
        doc.insert(ignore_permissions=True)
        existing_name = doc.name
    if tarabut_id:
        _save_local_mapping("supplier", tarabut_id, "Supplier", existing_name)
    return existing_name


def _save_local_mapping(
    entity_type: str, tarabut_id: str, erp_doctype: str, erp_name: str
):
    mapping_name = frappe.db.get_value(
        "Tarabut Entity Mapping",
        {"entity_type": entity_type, "tarabut_id": tarabut_id},
        "name",
    )
    mapping = (
        frappe.get_doc("Tarabut Entity Mapping", mapping_name)
        if mapping_name
        else frappe.new_doc("Tarabut Entity Mapping")
    )
    mapping.entity_type = entity_type
    mapping.tarabut_id = tarabut_id
    mapping.erp_doctype = erp_doctype
    mapping.erp_name = erp_name
    mapping.status = "Active"
    mapping.save(ignore_permissions=True)


def _settings():
    return frappe.get_single("Tarabut Connector Settings")


@frappe.whitelist()
def get_document_status(doctype: str, name: str):
    require_integration_user()
    if doctype not in ("Sales Order", "Purchase Order"):
        frappe.throw("Unsupported ERP document type")
    doc = frappe.get_doc(doctype, name)
    return {
        "doctype": doc.doctype,
        "name": doc.name,
        "docstatus": doc.docstatus,
        "status": doc.status,
        "modified": str(doc.modified),
    }


def _validate_company(company: str):
    if not frappe.db.exists("Company", company):
        frappe.throw(f"ERPNext Company does not exist: {company}")
