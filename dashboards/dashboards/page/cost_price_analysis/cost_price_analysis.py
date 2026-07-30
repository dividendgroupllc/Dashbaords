from __future__ import annotations

import frappe
from frappe.desk.utils import provide_binary_file

from dashboards.dashboards.cache import dashboard_cache
from dashboards.dashboards.page.cost_price_analysis.data import apply_view
from dashboards.dashboards.page.cost_price_analysis.data import (
    get_dashboard_context as get_cost_price_analysis_context,
)
from dashboards.dashboards.page.cost_price_analysis.export import build_filename, build_workbook


@frappe.whitelist()
@dashboard_cache("cost_price_analysis")
def get_dashboard_context(year=None, item_group=None):
    return get_cost_price_analysis_context(year=year, item_group=item_group)


@frappe.whitelist()
def export_xlsx(year=None, item_group=None, search=None, sort=None):
    """Отдать браузеру .xlsx с тем же набором строк, что показан на экране."""
    context = get_dashboard_context(year=year, item_group=item_group)
    rows = apply_view(context.get("rows") or [], search=search, sort=sort)

    provide_binary_file(build_filename(context), "xlsx", build_workbook(context, rows))
