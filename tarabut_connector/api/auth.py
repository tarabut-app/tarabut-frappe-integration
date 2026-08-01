import frappe


def require_integration_user():
    if frappe.session.user == "Administrator":
        return
    roles = set(frappe.get_roles(frappe.session.user))
    if not roles.intersection({"Tarabut Integration User", "System Manager"}):
        frappe.throw(
            "Tarabut Integration User role is required", frappe.PermissionError
        )
