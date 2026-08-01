import hashlib
import hmac
import json
import uuid
from datetime import datetime, timezone

import frappe
from frappe.integrations.utils import make_post_request
from frappe.utils.background_jobs import is_job_enqueued

DEFAULT_TARABUT_WEBHOOK_URL = "https://api.tarabut.app/webhooks/erp/erpnext"


def enqueue_document_change(doc, method=None):
    settings = frappe.get_single("Tarabut Connector Settings")
    if not settings.enabled:
        return

    job_id = f"tarabut-change:{doc.doctype}:{doc.name}"
    if is_job_enqueued(job_id):
        return
    frappe.enqueue(
        "tarabut_connector.api.webhook.send_document_change",
        queue="short",
        doc_type=doc.doctype,
        doc_name=doc.name,
        modified_at=str(doc.modified),
        item_code=getattr(doc, "item_code", None)
        or (doc.name if doc.doctype == "Item" else None),
        enqueue_after_commit=True,
        job_id=job_id,
    )


def send_document_change(
    doc_type: str,
    doc_name: str,
    modified_at: str,
    event_id: str | None = None,
    item_code: str | None = None,
):
    settings = frappe.get_single("Tarabut Connector Settings")
    if not settings.enabled:
        return
    webhook_url = settings.tarabut_webhook_url or DEFAULT_TARABUT_WEBHOOK_URL

    payload = {
        "connection_id": settings.tarabut_connection_id,
        "event_id": event_id or str(uuid.uuid4()),
        "doctype": doc_type,
        "name": doc_name,
        "modified_at": modified_at,
        "item_code": item_code,
    }
    raw_body = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    timestamp = str(int(datetime.now(timezone.utc).timestamp()))
    signature = hmac.new(
        settings.get_password("webhook_secret").encode("utf-8"),
        f"{timestamp}.{raw_body}".encode(),
        hashlib.sha256,
    ).hexdigest()

    sync = _get_or_create_sync(payload)
    try:
        make_post_request(
            webhook_url,
            data=raw_body,
            headers={
                "Content-Type": "application/json",
                "X-Tarabut-Signature": f"sha256={signature}",
                "X-Tarabut-Timestamp": timestamp,
            },
        )
        sync.status = "Succeeded"
        sync.error = None
        sync.save(ignore_permissions=True)
    except Exception as exc:
        sync.status = "Failed"
        sync.error = str(exc)
        sync.save(ignore_permissions=True)
        frappe.db.commit()
        raise


def retry_failed_notifications():
    """Retry failed event notifications while preserving the original event ID."""
    rows = frappe.get_all(
        "Tarabut Sync Record",
        filters={"direction": "outbound", "status": "Failed"},
        fields=["name", "idempotency_key", "payload"],
        order_by="modified asc",
        limit=100,
    )
    for row in rows:
        try:
            payload = json.loads(row.payload or "{}")
        except json.JSONDecodeError:
            continue
        job_id = f"tarabut-retry:{row.name}"
        if is_job_enqueued(job_id):
            continue
        frappe.enqueue(
            "tarabut_connector.api.webhook.send_document_change",
            queue="short",
            doc_type=payload.get("doctype"),
            doc_name=payload.get("name"),
            modified_at=payload.get("modified_at"),
            event_id=payload.get("event_id"),
            item_code=payload.get("item_code"),
            job_id=job_id,
        )


def _get_or_create_sync(payload):
    key = f"webhook:{payload['event_id']}"
    name = frappe.db.get_value("Tarabut Sync Record", {"idempotency_key": key})
    if name:
        sync = frappe.get_doc("Tarabut Sync Record", name)
        sync.status = "Processing"
        return sync
    sync = frappe.new_doc("Tarabut Sync Record")
    sync.idempotency_key = key
    sync.direction = "outbound"
    sync.entity_type = payload["doctype"]
    sync.tarabut_id = payload["name"]
    sync.status = "Processing"
    sync.payload = json.dumps(payload, default=str)
    sync.insert(ignore_permissions=True)
    return sync
