from __future__ import annotations

import frappe
from frappe.utils.dashboard import cache_source


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
    return {
        "labels": [
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
        ],
        "datasets": [{"name": "Сред чек", "values": [30307, 29884, 31480, 30855, 31695, 30698, 31019, 32194, 31802]}],
    }
