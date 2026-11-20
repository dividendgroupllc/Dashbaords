from __future__ import annotations

import frappe

ROL = "salesadmin"

# Sotuv rahbariga ochiladigan dashbordlar (egasi ro'yxati, 2026-11-20).
# investors / cost-price-analysis / manufacture-dashboard ATAYLAB yo'q.
PAGES = (
    "main-dashboard",
    "daily-dashboard",
    "monthly-analysis",
    "dividend-analysis",
    "product-comparison",
    "customer-comparison",
    "product-by-customer",
    "comparison-by-weight",
    "comparison-by-amount",
    "comparison-by-product",
)


def execute():
    """salesadmin rolini Dashboards workspace'i va sahifalarga QO'SHADI
    (ensure_dashboard_access'dan farqli: mavjud rollarni o'chirmaydi).
    Sahifa JSON'larida rol bor — bu patch workspace uchun va JSON sinxroni
    o'tkazib yuborilgan holatlar uchun (idempotent)."""
    _workspacega_qosh()
    for page in PAGES:
        _hujjatga_qosh("Page", page)
    _gl_entry_read()


def _gl_entry_read():
    """main-dashboard ichida P&L hisoboti yuguradi — GL Entry read shart.
    add_permission standart ruxsatlarni custom'ga ko'chirib keyin qo'shadi
    (bitta yalang'och Custom DocPerm qatori qolganlarini o'chirib yubormasin)."""
    if frappe.db.exists("Custom DocPerm", {"parent": "GL Entry", "role": ROL, "permlevel": 0}):
        return
    from frappe.permissions import add_permission
    add_permission("GL Entry", ROL, permlevel=0, ptype="read")


def _workspacega_qosh():
    if frappe.db.exists("Workspace", "Dashboards"):
        _hujjatga_qosh("Workspace", "Dashboards")


def _hujjatga_qosh(doctype, name):
    if not frappe.db.exists(doctype, name):
        return
    doc = frappe.get_doc(doctype, name)
    if ROL in {r.role for r in doc.get("roles", [])}:
        return
    doc.append("roles", {"role": ROL})
    doc.save(ignore_permissions=True)
