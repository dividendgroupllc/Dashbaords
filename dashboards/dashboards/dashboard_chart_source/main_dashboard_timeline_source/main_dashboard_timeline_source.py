from __future__ import annotations

import frappe
from frappe.utils.dashboard import cache_source


YEARLY_VALUES = {
    "2021": [22, 20, 37, 30, 29, 31, 33, 31, 39, 46, 53, 69],
    "2022": [26, 42, 46, 28, 37, 31, 33, 40, 47, 47, 42, 66],
    "2023": [32, 37, 36, 36, 43, 37, 39, 50, 47, 47, 47, 65],
    "2024": [32, 32, 31, 34, 28, 27, 28, 37, 34, 33, 33, 64],
}


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
    labels = []
    values = []

    for year, series in YEARLY_VALUES.items():
        for month_name, month_value in zip(
            [
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
            series,
        ):
            labels.append(f"{month_name}\n{year}")
            values.append(month_value)

    return {
        "labels": labels,
        "datasets": [
            {
                "name": "Sales",
                "values": values,
            }
        ],
    }
