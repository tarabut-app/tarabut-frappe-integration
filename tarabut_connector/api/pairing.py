import hashlib
import secrets
from urllib.parse import urlencode, urlparse, urlunparse

import frappe
from frappe import _
from frappe.utils import get_url

PAIRING_TTL_SECONDS = 10 * 60
INTEGRATION_USER = "tarabut-integration@tarabut.app"


@frappe.whitelist(methods=["POST"])
def create_pairing_session():
    """Create a short-lived authorization code from the trusted ERPNext side."""
    frappe.only_for("System Manager")

    settings = frappe.get_single("Tarabut Connector Settings")
    settings.validate()
    pairing_code = secrets.token_urlsafe(32)
    site_url = _public_site_url()
    companies = frappe.get_all(
        "Company", filters={"is_group": 0}, pluck="name", order_by="name asc"
    )
    frappe.cache.set_value(
        _cache_key(pairing_code),
        {
            "site_url": site_url,
            "companies": companies,
            "created_by": frappe.session.user,
        },
        expires_in_sec=PAIRING_TTL_SECONDS,
    )

    return {
        "connect_url": _connect_url(settings.tarabut_base_url, site_url, pairing_code),
        "expires_in": PAIRING_TTL_SECONDS,
    }


@frappe.whitelist(allow_guest=True, methods=["POST"])
def inspect_pairing_session(pairing_code: str):
    """Return non-secret setup choices for a valid pairing code."""
    session = _get_session(pairing_code)
    return {
        "site_url": session["site_url"],
        "companies": session["companies"],
        "expires_in": PAIRING_TTL_SECONDS,
    }


@frappe.whitelist(allow_guest=True, methods=["POST"])
def consume_pairing_session(pairing_code: str, company: str):
    """Consume a pairing code once and provision restricted API credentials."""
    cache_key = _cache_key(pairing_code)
    with frappe.cache.lock(f"{cache_key}:lock", timeout=10, blocking_timeout=3):
        session = _get_session(pairing_code)
        if company not in session["companies"]:
            frappe.throw(_("Select a company from this ERPNext site"))

        credentials = _provision_integration_user()
        frappe.cache.delete_value(cache_key)

    return {
        "site_url": session["site_url"],
        "company": company,
        **credentials,
    }


def _get_session(pairing_code: str):
    if not pairing_code or len(pairing_code) < 32:
        frappe.throw(_("The Tarabut pairing code is invalid or expired"))
    session = frappe.cache.get_value(_cache_key(pairing_code), expires=True)
    if not isinstance(session, dict):
        frappe.throw(_("The Tarabut pairing code is invalid or expired"))
    return session


def _cache_key(pairing_code: str):
    digest = hashlib.sha256((pairing_code or "").encode()).hexdigest()
    return f"tarabut-pairing:{digest}"


def _public_site_url(request=None):
    configured_url = _configured_public_site_url()
    if configured_url:
        return configured_url

    if request is None:
        request = getattr(frappe.local, "request", None)
    if request:
        headers = getattr(request, "headers", {}) or {}
        host = _first_header_value(headers.get("X-Forwarded-Host")) or getattr(
            request, "host", ""
        )
        scheme = _first_header_value(headers.get("X-Forwarded-Proto")) or getattr(
            request, "scheme", ""
        )
        if _is_safe_public_host(host):
            if scheme not in {"http", "https"}:
                scheme = "https"
            return f"{scheme}://{host}".rstrip("/")

    return get_url().rstrip("/")


def _configured_public_site_url():
    configured_url = (frappe.conf.get("tarabut_public_site_url") or "").strip()
    if not configured_url:
        return ""
    parsed = urlparse(configured_url)
    if parsed.scheme not in {"http", "https"} or not _is_safe_public_host(
        parsed.netloc
    ):
        frappe.throw(_("Tarabut public site URL is invalid"))
    return urlunparse((parsed.scheme, parsed.netloc, "", "", "", "")).rstrip("/")


def _first_header_value(value):
    if not value:
        return ""
    return str(value).split(",", 1)[0].strip()


def _is_safe_public_host(host):
    if not host:
        return False
    return not any(character.isspace() or character in "/\\@" for character in host)


def _connect_url(base_url: str, site_url: str, pairing_code: str):
    parsed = urlparse(base_url)
    hostname = parsed.hostname or ""
    if hostname.startswith("api."):
        hostname = f"seller.{hostname[4:]}"
    netloc = hostname
    if parsed.port:
        netloc = f"{netloc}:{parsed.port}"
    query = urlencode({"site_url": site_url, "pairing_code": pairing_code})
    return urlunparse(
        (parsed.scheme, netloc, "/settings/erp-integration", "", query, "")
    )


def _provision_integration_user():
    if frappe.db.exists("User", INTEGRATION_USER):
        user = frappe.get_doc("User", INTEGRATION_USER)
    else:
        user = frappe.get_doc(
            {
                "doctype": "User",
                "email": INTEGRATION_USER,
                "first_name": "Tarabut",
                "last_name": "Integration",
                "enabled": 1,
                "send_welcome_email": 0,
                "user_type": "System User",
            }
        )

    user.enabled = 1
    user.user_type = "System User"
    user.role_profile_name = None
    user.set("roles", [])
    user.append("roles", {"role": "Tarabut Integration User"})
    if not user.api_key:
        user.api_key = frappe.generate_hash(length=32)
    api_secret = frappe.generate_hash(length=32)
    user.api_secret = api_secret
    user.save(ignore_permissions=True)

    return {"api_key": user.api_key, "api_secret": api_secret}
