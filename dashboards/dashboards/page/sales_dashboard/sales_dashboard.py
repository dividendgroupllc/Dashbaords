from __future__ import annotations

from typing import Any

import frappe
from frappe.utils import flt, getdate, today

from dashboards.dashboards.dashboard_data import MONTH_LABELS, get_item_cogs_map, get_item_rcp_map


MONTHS = [{"key": label.lower(), "label": label} for label in MONTH_LABELS]
MONTH_MAP = {item["key"]: index + 1 for index, item in enumerate(MONTHS)}


def _get_years() -> list[str]:
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
	if years:
		return years

	return [str(getdate(today()).year)]


def _get_default_period() -> tuple[str, str]:
	latest_row = frappe.db.sql(
		"""
		SELECT MAX(posting_date) AS posting_date
		FROM `tabSales Invoice`
		WHERE docstatus = 1
		  AND COALESCE(is_return, 0) = 0
		""",
		as_dict=True,
	)[0]

	reference_date = getdate(latest_row.posting_date) if latest_row.posting_date else getdate(today())
	return str(reference_date.year), MONTH_LABELS[reference_date.month - 1].lower()


def _normalize_filters(year: str | None, month: str | None) -> tuple[str, str]:
	years = _get_years()
	default_year, default_month = _get_default_period()
	selected_year = year if year in years else default_year
	selected_month = month if month in MONTH_MAP else default_month
	return selected_year, selected_month


def _get_product_rows(year: str, month: str) -> list[dict[str, Any]]:
	cogs_map = get_item_cogs_map(year, MONTH_MAP[month])
	rcp_map = get_item_rcp_map(year, MONTH_MAP[month])
	rows = frappe.db.sql(
		"""
		SELECT
			COALESCE(NULLIF(sii.item_code, ''), NULLIF(sii.item_name, ''), 'Unknown Item') AS item_key,
			COALESCE(NULLIF(sii.item_name, ''), sii.item_code, 'Unknown Item') AS item,
			SUM(COALESCE(sii.stock_qty, sii.qty, 0)) AS kg,
			SUM(COALESCE(sii.base_net_amount, sii.net_amount, sii.base_amount, sii.amount, 0)) AS sales,
			SUM(COALESCE(sii.stock_qty, sii.qty, 0) * COALESCE(sii.incoming_rate, 0)) AS cost,
			0 AS rsp
		FROM `tabSales Invoice` si
		INNER JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
		WHERE si.docstatus = 1
		  AND COALESCE(si.is_return, 0) = 0
		  AND YEAR(si.posting_date) = %(year)s
		  AND MONTH(si.posting_date) = %(month)s
		GROUP BY
			COALESCE(NULLIF(sii.item_code, ''), NULLIF(sii.item_name, ''), 'Unknown Item'),
			COALESCE(NULLIF(sii.item_name, ''), sii.item_code, 'Unknown Item')
		ORDER BY sales DESC, item ASC
		""",
		{"year": int(year), "month": int(MONTH_MAP[month])},
		as_dict=True,
	)

	result = []
	for row in rows:
		sales = flt(row.sales)
		cost = flt(row.cost) or flt(cogs_map.get(row.item_key))
		margin = sales - cost
		rsp = flt(rcp_map.get(row.item_key))
		profit = margin - rsp
		result.append(
			{
				"item": row.item,
				"kg": round(flt(row.kg)),
				"sales": round(sales),
				"cost": round(cost),
				"margin": round(margin),
				"rsp": round(rsp),
				"margin_percent": (margin / sales * 100) if sales else 0,
				"profit": round(profit),
			}
		)

	return result


@frappe.whitelist()
def get_dashboard_context(year: str | None = None, month: str | None = None):
	selected_year, selected_month = _normalize_filters(year, month)

	return {
		"default_filters": {
			"year": selected_year,
			"month": selected_month,
		},
		"years": _get_years(),
		"months": MONTHS,
		"product_rows": _get_product_rows(selected_year, selected_month),
	}
