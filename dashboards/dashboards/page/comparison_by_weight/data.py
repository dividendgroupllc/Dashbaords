from __future__ import annotations

from collections import defaultdict
from typing import Any

import frappe
from frappe.utils import cint, flt

from dashboards.dashboards.dashboard_data import MONTH_LABELS, format_number


ROW_LIMIT = 30


MONTHS = [{"key": label.lower(), "label": label} for label in MONTH_LABELS]
MONTH_MAP = {item["key"]: index + 1 for index, item in enumerate(MONTHS)}


def _get_years(limit: int = 4) -> list[str]:
	rows = frappe.db.sql(
		"""
		SELECT DISTINCT YEAR(posting_date) AS year
		FROM `tabSales Invoice`
		WHERE docstatus = 1
		  AND COALESCE(is_return, 0) = 0
		  AND posting_date IS NOT NULL
		ORDER BY year
		""",
		as_dict=True,
	)

	years = [str(row.year) for row in rows if row.year]
	if limit and len(years) > limit:
		years = years[-limit:]
	return years


def _get_default_month() -> str:
	latest_row = frappe.db.sql(
		"""
		SELECT MAX(posting_date) AS posting_date
		FROM `tabSales Invoice`
		WHERE docstatus = 1
		  AND COALESCE(is_return, 0) = 0
		""",
		as_dict=True,
	)[0]

	if latest_row.posting_date:
		month_no = latest_row.posting_date.month
		return MONTH_LABELS[month_no - 1].lower()

	return MONTH_LABELS[0].lower()


def _normalize_month(month: str | None) -> str:
	return month if month in MONTH_MAP else _get_default_month()


def _format_int(value: float | int) -> str:
	return format_number(round(flt(value)), precision=0)


def _get_client_rows(selected_month: str, years: list[str]) -> list[dict[str, Any]]:
	rows = frappe.db.sql(
		"""
		SELECT
			COALESCE(NULLIF(si.customer_name, ''), si.customer, 'Unknown Client') AS customer_name,
			YEAR(si.posting_date) AS year,
			SUM(COALESCE(sii.stock_qty, sii.qty, 0)) AS qty
		FROM `tabSales Invoice` si
		INNER JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
		WHERE si.docstatus = 1
		  AND COALESCE(si.is_return, 0) = 0
		  AND MONTH(si.posting_date) = %(month_no)s
		  AND YEAR(si.posting_date) IN %(years)s
		GROUP BY COALESCE(NULLIF(si.customer_name, ''), si.customer, 'Unknown Client'), YEAR(si.posting_date)
		""",
		{"month_no": MONTH_MAP[selected_month], "years": tuple(cint(year) for year in years)},
		as_dict=True,
	)

	grouped: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
	totals_by_year = defaultdict(float)

	for row in rows:
		label = row.customer_name or "Unknown Client"
		year = str(row.year)
		value = flt(row.qty)
		grouped[label][year] += value
		totals_by_year[year] += value

	ordered_labels = sorted(grouped, key=lambda label: (-sum(grouped[label].values()), label))[:ROW_LIMIT]
	result = []

	for label in ordered_labels:
		total_value = sum(grouped[label].values())
		values = [grouped[label].get(year, 0) for year in years]
		result.append(
			{
				"label": label,
				"values": [_format_int(value) if value else "" for value in values],
				"total": _format_int(total_value) if total_value else "",
			}
		)

	grand_total = sum(totals_by_year.values())
	result.append(
		{
			"label": "Total",
			"values": [_format_int(totals_by_year.get(year, 0)) if totals_by_year.get(year, 0) else "" for year in years],
			"total": _format_int(grand_total) if grand_total else "",
			"is_total": True,
		}
	)

	return result


def _get_item_rows(selected_month: str, years: list[str]) -> list[dict[str, Any]]:
	rows = frappe.db.sql(
		"""
		SELECT
			COALESCE(NULLIF(sii.item_name, ''), sii.item_code, 'Unknown Item') AS item_name,
			YEAR(si.posting_date) AS year,
			SUM(COALESCE(sii.stock_qty, sii.qty, 0)) AS qty,
			SUM(COALESCE(sii.base_net_amount, sii.net_amount, sii.base_amount, sii.amount, 0)) AS amount
		FROM `tabSales Invoice` si
		INNER JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
		WHERE si.docstatus = 1
		  AND COALESCE(si.is_return, 0) = 0
		  AND MONTH(si.posting_date) = %(month_no)s
		  AND YEAR(si.posting_date) IN %(years)s
		GROUP BY COALESCE(NULLIF(sii.item_name, ''), sii.item_code, 'Unknown Item'), YEAR(si.posting_date)
		""",
		{"month_no": MONTH_MAP[selected_month], "years": tuple(cint(year) for year in years)},
		as_dict=True,
	)

	grouped: dict[str, dict[str, dict[str, float]]] = defaultdict(
		lambda: defaultdict(lambda: {"qty": 0.0, "amount": 0.0})
	)
	totals_by_year = defaultdict(lambda: {"qty": 0.0, "amount": 0.0})

	for row in rows:
		label = row.item_name or "Unknown Item"
		year = str(row.year)
		qty = flt(row.qty)
		amount = flt(row.amount)
		grouped[label][year]["qty"] += qty
		grouped[label][year]["amount"] += amount
		totals_by_year[year]["qty"] += qty
		totals_by_year[year]["amount"] += amount

	ordered_labels = sorted(
		grouped,
		key=lambda label: (-sum(grouped[label][year]["qty"] for year in grouped[label]), label),
	)[:ROW_LIMIT]

	result = []
	for label in ordered_labels:
		row_values = []
		total_qty = 0.0
		total_amount = 0.0
		for year in years:
			qty = grouped[label][year]["qty"]
			amount = grouped[label][year]["amount"]
			avg_price = amount / qty if qty else 0
			total_qty += qty
			total_amount += amount
			row_values.extend([_format_int(qty) if qty else "", _format_int(avg_price) if avg_price else ""])

		total_avg_price = total_amount / total_qty if total_qty else 0
		result.append(
			{
				"label": label,
				"values": row_values,
				"total_qty": _format_int(total_qty) if total_qty else "",
				"total_avg": _format_int(total_avg_price) if total_avg_price else "",
			}
		)

	total_values = []
	grand_total_qty = 0.0
	grand_total_amount = 0.0
	for year in years:
		qty = totals_by_year[year]["qty"]
		amount = totals_by_year[year]["amount"]
		avg_price = amount / qty if qty else 0
		grand_total_qty += qty
		grand_total_amount += amount
		total_values.extend([_format_int(qty) if qty else "", _format_int(avg_price) if avg_price else ""])

	grand_total_avg_price = grand_total_amount / grand_total_qty if grand_total_qty else 0

	result.append(
		{
			"label": "Total",
			"values": total_values,
			"total_qty": _format_int(grand_total_qty) if grand_total_qty else "",
			"total_avg": _format_int(grand_total_avg_price) if grand_total_avg_price else "",
			"is_total": True,
		}
	)

	return result


def get_dashboard_context(month: str | None = None) -> dict[str, Any]:
	selected_month = _normalize_month(month)
	years = _get_years()

	return {
		"selected_month": selected_month,
		"months": MONTHS,
		"years": years,
		"customer_rows": _get_client_rows(selected_month, years),
		"item_rows": _get_item_rows(selected_month, years),
		"customer_title": "Клиент кг",
		"item_title": "Предмет кг",
		"qty_title": "КГ",
		"avg_title": "Сред цена",
		"total_qty_title": "KG",
		"total_avg_title": "Сред цена",
		"total_title": "Total",
	}
