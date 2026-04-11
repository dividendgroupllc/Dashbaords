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
        ],
        "datasets": [{"name": "Сред себ", "values": [24286, 24789, 24397, 24616, 23469, 24912, 24067, 22394]}],
    }
