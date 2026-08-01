import hashlib
import hmac
import json
import uuid

import frappe


DEFAULT_TARABUT_WEBHOOK_URL = "https://api.tarabut.app/webhooks/erp/erpnext"


def enqueue_document_change(doc, method=None):
    settings = frappe.get_single("Tarabut Connector Settings")
    if not settings.enabled:
        return

    frappe.enqueue(
        "tarabut_connector.api.webhook.send_document_change",
        queue="short",
        doc_type=doc.doctype,
        doc_name=doc.name,
        modified_at=str(doc.modified),
    )


def send_document_change(doc_type: str, doc_name: str, modified_at: str):
    settings = frappe.get_single("Tarabut Connector Settings")
    if not settings.enabled:
        return
    webhook_url = settings.tarabut_webhook_url or DEFAULT_TARABUT_WEBHOOK_URL

    payload = {
        "connection_id": settings.tarabut_connection_id,
        "event_id": str(uuid.uuid4()),
        "doctype": doc_type,
        "name": doc_name,
        "modified_at": modified_at,
    }
    raw_body = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    signature = hmac.new(
        settings.get_password("webhook_secret").encode("utf-8"),
        raw_body.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    frappe.make_post_request(
        webhook_url,
        data=raw_body,
        headers={
            "Content-Type": "application/json",
            "X-Tarabut-Signature": f"sha256={signature}",
        },
    )
