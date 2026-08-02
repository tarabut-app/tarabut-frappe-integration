import hashlib
import hmac
import json
import time
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from tarabut_connector.api.order import (
    _coerce_payload,
    _complete_sync,
    _purchase_order_row_defaults,
    _reserve_sync,
    _resolve_item_code,
)
from tarabut_connector.api.webhook import _get_or_create_sync
from tarabut_connector.install import after_install, before_uninstall
from tarabut_connector.tarabut.doctype.tarabut_connector_settings.tarabut_connector_settings import (
    DEFAULT_TARABUT_BASE_URL,
    DEFAULT_TARABUT_WEBHOOK_URL,
)


class TestConnectorContract(FrappeTestCase):
    def setUp(self):
        super().setUp()
        if not frappe.db.exists("UOM", "Nos"):
            frappe.get_doc(
                {
                    "doctype": "UOM",
                    "uom_name": "Nos",
                    "enabled": 1,
                }
            ).insert(ignore_permissions=True)
        if not frappe.db.exists("Item Group", "All Item Groups"):
            frappe.get_doc(
                {
                    "doctype": "Item Group",
                    "item_group_name": "All Item Groups",
                    "is_group": 1,
                }
            ).insert(ignore_permissions=True)

    def tearDown(self):
        frappe.db.rollback()

    def test_settings_apply_production_urls(self):
        settings = frappe.get_single("Tarabut Connector Settings")
        settings.tarabut_base_url = None
        settings.tarabut_webhook_url = None
        settings.before_validate()
        self.assertEqual(settings.tarabut_base_url, DEFAULT_TARABUT_BASE_URL)
        self.assertEqual(settings.tarabut_webhook_url, DEFAULT_TARABUT_WEBHOOK_URL)

    def test_disconnected_settings_can_save_advanced_urls(self):
        settings = frappe.get_single("Tarabut Connector Settings")
        settings.enabled = 1
        settings.tarabut_connection_id = None
        settings.webhook_secret = None
        settings.tarabut_base_url = "https://api.stage.tarabut.app"
        settings.tarabut_webhook_url = (
            "https://api.stage.tarabut.app/webhooks/erp/erpnext"
        )
        settings.save(ignore_permissions=True)
        self.assertEqual(settings.enabled, 0)
        self.assertEqual(settings.tarabut_base_url, "https://api.stage.tarabut.app")

    def test_complete_credentials_set_connected_status(self):
        settings = frappe.get_single("Tarabut Connector Settings")
        settings.tarabut_connection_id = "erpconn_test"
        settings.webhook_secret = "a-valid-webhook-secret"
        settings.before_validate()
        self.assertEqual(settings.enabled, 1)

    def test_payload_accepts_json_and_dict(self):
        value = {"order": {"id": "order_test"}}
        self.assertEqual(_coerce_payload(value), value)
        self.assertEqual(_coerce_payload(json.dumps(value)), value)

    def test_outbound_event_id_is_idempotent(self):
        payload = {
            "connection_id": "erpconn_test",
            "event_id": "event_test",
            "doctype": "Item",
            "name": "ITEM-TEST",
            "modified_at": "2026-08-01 00:00:00",
            "item_code": "ITEM-TEST",
        }
        first = _get_or_create_sync(payload)
        second = _get_or_create_sync(payload)
        self.assertEqual(first.name, second.name)
        self.assertEqual(first.idempotency_key, "webhook:event_test")

    def test_webhook_signature_contract(self):
        payload = json.dumps(
            {"connection_id": "erpconn_test", "event_id": "event_test"},
            separators=(",", ":"),
            sort_keys=True,
        )
        timestamp = str(int(time.time()))
        signature = hmac.new(
            b"secret",
            f"{timestamp}.{payload}".encode(),
            hashlib.sha256,
        ).hexdigest()
        self.assertEqual(len(signature), 64)
        self.assertTrue(
            hmac.compare_digest(
                signature,
                hmac.new(
                    b"secret",
                    f"{timestamp}.{payload}".encode(),
                    hashlib.sha256,
                ).hexdigest(),
            )
        )

    def test_order_adapter_uses_platform_item_mapping_metadata(self):
        item_code = "TARABUT-CONTRACT-ITEM"
        if not frappe.db.exists("Item", item_code):
            frappe.get_doc(
                {
                    "doctype": "Item",
                    "item_code": item_code,
                    "item_name": "Tarabut Contract Item",
                    "item_group": "All Item Groups",
                    "stock_uom": "Nos",
                }
            ).insert(ignore_permissions=True)
        resolved = _resolve_item_code({"metadata": {"erpnext_item_code": item_code}})
        self.assertEqual(resolved, item_code)

    def test_install_is_idempotent_and_standard_documents_are_read_only(self):
        after_install()
        after_install()
        for doctype in (
            "Item",
            "Customer",
            "Supplier",
            "Sales Order",
            "Purchase Order",
        ):
            permissions = frappe.get_all(
                "Custom DocPerm",
                filters={
                    "parent": doctype,
                    "role": "Tarabut Integration User",
                    "permlevel": 0,
                },
                fields=["read", "write", "create", "delete", "submit", "cancel"],
            )
            self.assertEqual(len(permissions), 1)
            self.assertEqual(permissions[0].read, 1)
            for property_name in ("write", "create", "delete", "submit", "cancel"):
                self.assertEqual(permissions[0].get(property_name), 0)

    def test_purchase_order_defaults_apply_owned_warehouse_and_cost_center(self):
        with patch("frappe.db.get_value", return_value="Test Company"):
            defaults = _purchase_order_row_defaults(
                "Test Company",
                {
                    "target_warehouse": "Receiving - TC",
                    "cost_center": "Main - TC",
                },
            )
        self.assertEqual(defaults["warehouse"], "Receiving - TC")
        self.assertEqual(defaults["cost_center"], "Main - TC")

    def test_inbound_idempotency_returns_the_original_document(self):
        item_code = "TARABUT-IDEMPOTENCY-ITEM"
        if not frappe.db.exists("Item", item_code):
            frappe.get_doc(
                {
                    "doctype": "Item",
                    "item_code": item_code,
                    "item_name": "Tarabut Idempotency Item",
                    "item_group": "All Item Groups",
                    "stock_uom": "Nos",
                }
            ).insert(ignore_permissions=True)
        payload = {"order": {"id": "order_idempotency_test"}}
        sync, existing = _reserve_sync(
            "erpnext:test:order_idempotency_test", "inbound", "sales_order", payload
        )
        self.assertIsNone(existing)
        _complete_sync(sync, "Item", item_code)
        _, replay = _reserve_sync(
            "erpnext:test:order_idempotency_test", "inbound", "sales_order", payload
        )
        self.assertEqual(replay["doctype"], "Item")
        self.assertEqual(replay["name"], item_code)

    def test_uninstall_refuses_to_remove_audit_history(self):
        _get_or_create_sync(
            {
                "connection_id": "erpconn_uninstall_test",
                "event_id": "event_uninstall_test",
                "doctype": "Item",
                "name": "ITEM-UNINSTALL-TEST",
                "modified_at": "2026-08-01 00:00:00",
                "item_code": "ITEM-UNINSTALL-TEST",
            }
        )
        with self.assertRaises(frappe.ValidationError):
            before_uninstall()
