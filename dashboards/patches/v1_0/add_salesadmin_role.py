from __future__ import annotations

import frappe

# DIQQAT: nom prod'da qo'lda yaratilgan rol bilan AYNAN mos bo'lishi shart
ROL = "salesadmin"


def execute():
    """Rol JSON sinxronidan OLDIN mavjud bo'lishi kerak (pre_model_sync) —
    sahifa JSON'laridagi Has Role qatorlari shu rolga ishora qiladi."""
    if not frappe.db.exists("Role", ROL):
        frappe.get_doc({
            "doctype": "Role",
            "role_name": ROL,
            "desk_access": 1,
        }).insert(ignore_permissions=True)
