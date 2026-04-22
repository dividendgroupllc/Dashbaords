from __future__ import annotations

import frappe
from frappe.utils.dashboard import cache_source

from dashboards.dashboards.page.page_dashboard.data import get_avg_check_chart_data


@frappe.whitelist()
@cache_source
def get_data(
    chart_name=None,
    chart=None,
    no_cache=None,
    filters=None,
    from_date=None,
    to_date=None,
    timespan=None,
    time_interval=None,
    heatmap_year=None,
):
    parsed_filters = frappe.parse_json(filters) if filters and not isinstance(filters, dict) else (filters or {})
    return get_avg_check_chart_data(parsed_filters.get("year"))
