import hashlib
import json

import frappe
from frappe.utils import cint, flt

from tarabut_connector.api.auth import require_integration_user


@frappe.whitelist()
def list_products(
    company: str,
    price_list: str,
    warehouses=None,
    cursor: str | int | None = None,
    limit: str | int = 100,
    modified_since: str | None = None,
):
    require_integration_user()
    _validate_company_and_price_list(company, price_list)
    warehouse_names = _coerce_list(warehouses)
    _validate_warehouses(company, warehouse_names)
    page_limit = min(max(cint(limit), 1), 500)
    offset = max(cint(cursor), 0)
    filters = {"is_sales_item": 1}
    if modified_since:
        filters["modified"] = (">", modified_since)

    items = frappe.get_all(
        "Item",
        filters=filters,
        fields=["name"],
        start=offset,
        page_length=page_limit,
        order_by="modified asc, name asc",
    )
    products = [
        _build_product_snapshot(row.name, company, price_list, warehouse_names)
        for row in items
    ]
    return {
        "items": products,
        "next_cursor": str(offset + len(items)) if len(items) == page_limit else None,
    }


@frappe.whitelist()
def get_product_snapshot(
    item_code: str,
    company: str,
    price_list: str,
    warehouses=None,
):
    require_integration_user()
    _validate_company_and_price_list(company, price_list)
    warehouse_names = _coerce_list(warehouses)
    _validate_warehouses(company, warehouse_names)
    return _build_product_snapshot(item_code, company, price_list, warehouse_names)


def _build_product_snapshot(item_code, company, price_list, warehouses):
    if not frappe.db.exists("Item", item_code):
        frappe.throw(f"ERPNext Item does not exist: {item_code}")
    item = frappe.get_doc("Item", item_code)
    if item.variant_of:
        template_code = item.variant_of
    else:
        template_code = item.name

    uoms = {item.stock_uom}
    for row in item.get("uoms") or []:
        if row.uom:
            uoms.add(row.uom)

    prices = frappe.get_all(
        "Item Price",
        filters={
            "item_code": item.name,
            "price_list": price_list,
            "selling": 1,
        },
        fields=["name", "uom", "currency", "price_list_rate", "modified"],
        order_by="valid_from desc, modified desc",
    )
    bins = []
    if warehouses:
        bins = frappe.get_all(
            "Bin",
            filters={"item_code": item.name, "warehouse": ("in", warehouses)},
            fields=[
                "name",
                "warehouse",
                "actual_qty",
                "projected_qty",
                "reserved_qty",
                "planned_qty",
                "modified",
            ],
        )

    payload = {
        "external_key": f"{company}:{item.name}",
        "company": company,
        "item_code": item.name,
        "template_code": template_code,
        "item_name": item.item_name,
        "description": item.description,
        "disabled": bool(item.disabled),
        "stock_uom": item.stock_uom,
        "uoms": sorted(uoms),
        "prices": [
            {
                "name": row.name,
                "uom": row.uom or item.stock_uom,
                "currency": row.currency,
                "rate": flt(row.price_list_rate),
                "modified": str(row.modified),
            }
            for row in prices
        ],
        "bins": [
            {
                "name": row.name,
                "warehouse": row.warehouse,
                "actual_qty": flt(row.actual_qty),
                "projected_qty": flt(row.projected_qty),
                "available_qty": max(flt(row.actual_qty) - flt(row.reserved_qty), 0),
                "modified": str(row.modified),
            }
            for row in bins
        ],
        "modified": str(item.modified),
    }
    payload["fingerprint"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()
    return payload


def _coerce_list(value):
    if value is None or value == "":
        return []
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else [value]
        except json.JSONDecodeError:
            return [part.strip() for part in value.split(",") if part.strip()]
    return list(value)


def _validate_company_and_price_list(company, price_list):
    if not frappe.db.exists("Company", company):
        frappe.throw(f"ERPNext Company does not exist: {company}")
    if not frappe.db.exists("Price List", price_list):
        frappe.throw(f"ERPNext Price List does not exist: {price_list}")


def _validate_warehouses(company, warehouses):
    for warehouse in warehouses:
        actual_company = frappe.db.get_value("Warehouse", warehouse, "company")
        if actual_company != company:
            frappe.throw(f"Warehouse {warehouse} does not belong to {company}")
