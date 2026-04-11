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
            "October",
            "November",
            "December",
        ],
        "datasets": [
            {
                "name": "2024",
                "values": [18, 19, 20, 20, 16, 17, 18, 23, 25, 22, 24, 39],
            },
            {
                "name": "2023",
                "values": [16, 18, 19, 18, 17, 16, 17, 19, 21, 20, 19, 35],
            },
        ],
    }
