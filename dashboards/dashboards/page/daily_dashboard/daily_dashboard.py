from __future__ import annotations

from calendar import monthrange
from typing import Any

import frappe
from frappe.utils import flt, getdate, today

from dashboards.dashboards.dashboard_data import MONTH_LABELS


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


def _normalize_day(year: str, month: str, day: str | int | None) -> int | None:
	if day in (None, ""):
		return None

	try:
		day_no = int(day)
	except (TypeError, ValueError):
		return None

	last_day = monthrange(int(year), MONTH_MAP[month])[1]
	return day_no if 1 <= day_no <= last_day else None


def _base_filter_clause(year: str, month: str, alias: str = "si") -> tuple[str, dict[str, Any]]:
	prefix = f"{alias}." if alias else ""
	return (
		f" AND YEAR({prefix}posting_date) = %(year)s AND MONTH({prefix}posting_date) = %(month)s",
		{"year": int(year), "month": int(MONTH_MAP[month])},
	)


def _client_filter_clause(client: str | None, params: dict[str, Any], alias: str = "si") -> str:
	if not client:
		return ""

	params["client"] = client
	return (
		f" AND COALESCE(NULLIF({alias}.customer_name, ''), {alias}.customer, 'Неизвестный клиент') = %(client)s"
	)


def _day_filter_clause(day: int | None, params: dict[str, Any], alias: str = "si") -> str:
	if not day:
		return ""

	prefix = f"{alias}." if alias else ""
	params["day"] = int(day)
	return f" AND DAY({prefix}posting_date) = %(day)s"


def _get_clients(year: str, month: str, day: int | None = None) -> list[str]:
	clause, params = _base_filter_clause(year, month, alias="si")
	day_clause = _day_filter_clause(day, params, alias="si")
	rows = frappe.db.sql(
		f"""
		SELECT
			COALESCE(NULLIF(si.customer_name, ''), si.customer, 'Неизвестный клиент') AS client,
			SUM(COALESCE(sii.base_net_amount, sii.net_amount, sii.base_amount, sii.amount, 0)) AS sales_amount
		FROM `tabSales Invoice` si
		INNER JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
		WHERE si.docstatus = 1
		  AND COALESCE(si.is_return, 0) = 0
		{clause}
		{day_clause}
		GROUP BY COALESCE(NULLIF(si.customer_name, ''), si.customer, 'Неизвестный клиент')
		ORDER BY sales_amount DESC, client ASC
		""",
		params,
		as_dict=True,
	)
	return [row.client for row in rows if row.client]


def _get_calendar_values(year: str, month: str, client: str | None) -> dict[int, int]:
	clause, params = _base_filter_clause(year, month, alias="si")
	client_clause = _client_filter_clause(client, params, alias="si")
	rows = frappe.db.sql(
		f"""
		SELECT
			DAY(si.posting_date) AS day_no,
			SUM(COALESCE(sii.stock_qty, sii.qty, 0)) AS total_qty
		FROM `tabSales Invoice` si
		INNER JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
		WHERE si.docstatus = 1
		  AND COALESCE(si.is_return, 0) = 0
		{clause}
		{client_clause}
		GROUP BY DAY(si.posting_date)
		ORDER BY DAY(si.posting_date)
		""",
		params,
		as_dict=True,
	)
	return {int(row.day_no): int(round(flt(row.total_qty))) for row in rows if row.day_no}


def _get_product_rows(year: str, month: str, client: str | None, day: int | None = None) -> list[dict[str, Any]]:
	clause, params = _base_filter_clause(year, month, alias="si")
	client_clause = _client_filter_clause(client, params, alias="si")
	day_clause = _day_filter_clause(day, params, alias="si")
	rows = frappe.db.sql(
		f"""
		SELECT
			COALESCE(NULLIF(sii.item_name, ''), sii.item_code, 'Неизвестный товар') AS item,
			SUM(COALESCE(sii.stock_qty, sii.qty, 0)) AS kg,
			SUM(COALESCE(sii.base_net_amount, sii.net_amount, sii.base_amount, sii.amount, 0)) AS sales,
			SUM(COALESCE(sii.stock_qty, sii.qty, 0) * COALESCE(sii.incoming_rate, 0)) AS cost,
			SUM(COALESCE(sii.discount_amount, 0) + COALESCE(sii.distributed_discount_amount, 0)) AS rsp
		FROM `tabSales Invoice` si
		INNER JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
		WHERE si.docstatus = 1
		  AND COALESCE(si.is_return, 0) = 0
		{clause}
		{client_clause}
		{day_clause}
		GROUP BY COALESCE(NULLIF(sii.item_name, ''), sii.item_code, 'Неизвестный товар')
		ORDER BY sales DESC, item ASC
		""",
		params,
		as_dict=True,
	)

	result = []
	for row in rows:
		sales = flt(row.sales)
		cost = flt(row.cost)
		margin = sales - cost
		rsp = flt(row.rsp)
		np = margin - rsp
		result.append(
			{
				"item": row.item,
				"kg": round(flt(row.kg)),
				"sales": round(sales),
				"cost": round(cost),
				"margin": round(margin),
				"rsp": round(rsp),
				"profitability": (margin / sales * 100) if sales else 0,
				"np": round(np),
				"np_profitability": (np / sales * 100) if sales else 0,
			}
		)

	return result


@frappe.whitelist()
def get_dashboard_context(
	year: str | None = None,
	month: str | None = None,
	client: str | None = None,
	day: str | int | None = None,
):
	selected_year, selected_month = _normalize_filters(year, month)
	selected_day = _normalize_day(selected_year, selected_month, day)
	clients = _get_clients(selected_year, selected_month, selected_day)
	selected_client = client if client in clients else None

	calendar_values = _get_calendar_values(selected_year, selected_month, selected_client)
	product_rows = _get_product_rows(selected_year, selected_month, selected_client, selected_day)
	month_label = next((item["label"] for item in MONTHS if item["key"] == selected_month), selected_month.title())
	total_days = monthrange(int(selected_year), MONTH_MAP[selected_month])[1]

	return {
		"title_primary": "3 ИНФОРМАЦИОННАЯ ПАНЕЛЬ",
		"title_secondary": "КОМПАНИЯ",
		"default_filters": {
			"year": selected_year,
			"month": selected_month,
			"client": selected_client,
			"day": selected_day,
		},
		"years": _get_years(),
		"months": MONTHS,
		"clients": clients,
		"calendar_values": calendar_values,
		"product_rows": product_rows,
		"calendar_meta": {
			"label": f"{month_label} {selected_year}",
			"days_in_month": total_days,
			"selected_day": selected_day,
		},
	}
