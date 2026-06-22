from __future__ import annotations

import frappe


def execute():
    """Detach the Dashboards workspace from the Dashboards module (module = NULL).

    The workspace JSON file was removed from the app, so ``bench migrate`` no
    longer re-imports it. However existing sites still carry the stale
    ``module = "Dashboards"`` value (originally written by the workspace file
    import and by ``ensure_dashboard_access``). With a module set, the workspace
    is gated behind module access and stays hidden from users who only have the
    role. Clearing it makes it a plain public workspace shown purely by role.

    ``frappe.db.set_value`` is used deliberately (raw DB write) so it does NOT
    trigger ``Workspace.on_update`` — i.e. it will not try to re-export a file
    under developer mode. Runs once per site via the patch log.
    """
    if not frappe.db.exists("Workspace", "Dashboards"):
        return

    frappe.db.set_value("Workspace", "Dashboards", "module", None, update_modified=False)
