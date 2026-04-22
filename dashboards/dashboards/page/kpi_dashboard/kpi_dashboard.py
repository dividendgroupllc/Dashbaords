from __future__ import annotations

from typing import Any

import frappe
from frappe.utils import flt, getdate, today

from dashboards.dashboards.dashboard_data import MONTH_LABELS, format_number


def get_dashboard_years() -> list[str]:
	rows = frappe.db.sql(
		"""
		SELECT DISTINCT YEAR(posting_date) AS year
		FROM `tabSales Invoice`
		WHERE docstatus = 1
		  AND posting_date IS NOT NULL
		ORDER BY year
		""",
		as_dict=True,
	)

	values = [str(row.year) for row in rows if row.year]
	if values:
		return values

	return [str(getdate(today()).year)]


def get_default_period(selected_year: str | None = None) -> tuple[str, str]:
	years = get_dashboard_years()
	year = selected_year if selected_year in years else years[-1]

	latest_row = frappe.db.sql(
		"""
		SELECT MAX(posting_date) AS posting_date
		FROM `tabSales Invoice`
		WHERE docstatus = 1
		  AND YEAR(posting_date) = %(year)s
		""",
		{"year": int(year)},
		as_dict=True,
	)[0]

	if latest_row.posting_date:
		month = MONTH_LABELS[getdate(latest_row.posting_date).month - 1]
	else:
		month = MONTH_LABELS[0]

	return year, month


def _get_period_params(year: str, month: str | None = None) -> dict[str, int]:
	params = {"year": int(year)}
	if month in MONTH_LABELS:
		params["month"] = MONTH_LABELS.index(month) + 1
	return params


def _period_clause(year: str, month: str | None = None, alias: str = "") -> tuple[str, dict[str, int]]:
	prefix = f"{alias}." if alias else ""
	params = _get_period_params(year, month)
	clause = f" AND YEAR({prefix}posting_date) = %(year)s"
	if "month" in params:
		clause += f" AND MONTH({prefix}posting_date) = %(month)s"
	return clause, params


def _get_kpi_totals(year: str, month: str | None) -> dict[str, str]:
	invoice_clause, invoice_params = _period_clause(year, month)
	item_clause, item_params = _period_clause(year, month, alias="si")

	invoice_totals = frappe.db.sql(
		f"""
		SELECT
			SUM(CASE WHEN COALESCE(is_return, 0) = 1 THEN ABS(COALESCE(base_net_total, net_total, 0)) ELSE 0 END) AS return_total,
			SUM(CASE WHEN COALESCE(is_return, 0) = 0 THEN COALESCE(loyalty_amount, 0) ELSE 0 END) AS loyalty_bonus
		FROM `tabSales Invoice`
		WHERE docstatus = 1
		{invoice_clause}
		""",
		invoice_params,
		as_dict=True,
	)[0]

	item_totals = frappe.db.sql(
		f"""
		SELECT
			SUM(COALESCE(sii.base_net_amount, sii.net_amount, sii.base_amount, sii.amount, 0)) AS sales_total,
			SUM(COALESCE(sii.stock_qty, sii.qty, 0) * COALESCE(sii.incoming_rate, 0)) AS cost_total,
			SUM(COALESCE(sii.discount_amount, 0) + COALESCE(sii.distributed_discount_amount, 0)) AS discount_total,
			SUM(
				CASE
					WHEN COALESCE(sii.is_free_item, 0) = 1
						THEN COALESCE(sii.base_price_list_rate, sii.price_list_rate, 0) * COALESCE(sii.qty, 0)
					ELSE 0
				END
			) AS free_item_bonus
		FROM `tabSales Invoice` si
		INNER JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
		WHERE si.docstatus = 1
		  AND COALESCE(si.is_return, 0) = 0
		{item_clause}
		""",
		item_params,
		as_dict=True,
	)[0]

	sales_total = flt(item_totals.sales_total)
	cost_total = flt(item_totals.cost_total)
	margin_total = sales_total - cost_total
	discount_total = flt(item_totals.discount_total)
	bonus_total = flt(item_totals.free_item_bonus) + flt(invoice_totals.loyalty_bonus)

	return {
		"sales": format_number(sales_total),
		"margin": format_number(margin_total),
		"margin_minus_discount": format_number(margin_total - discount_total),
		"returns": format_number(invoice_totals.return_total),
		"bonus": format_number(bonus_total),
		"discount": format_number(discount_total),
	}


def _get_client_metrics(year: str, month: str | None = None) -> list[dict[str, Any]]:
	item_clause, item_params = _period_clause(year, month, alias="si")
	invoice_clause, invoice_params = _period_clause(year, month)

	sales_rows = frappe.db.sql(
		f"""
		SELECT
			COALESCE(NULLIF(si.customer_name, ''), si.customer, 'Unknown Client') AS client,
			SUM(COALESCE(sii.base_net_amount, sii.net_amount, sii.base_amount, sii.amount, 0)) AS sales_amount,
			SUM(COALESCE(sii.stock_qty, sii.qty, 0) * COALESCE(sii.incoming_rate, 0)) AS cost_amount,
			SUM(COALESCE(sii.stock_qty, sii.qty, 0)) AS qty_total,
			SUM(COALESCE(sii.discount_amount, 0) + COALESCE(sii.distributed_discount_amount, 0)) AS discount_total,
			SUM(
				CASE
					WHEN COALESCE(sii.is_free_item, 0) = 1
						THEN COALESCE(sii.base_price_list_rate, sii.price_list_rate, 0) * COALESCE(sii.qty, 0)
					ELSE 0
				END
			) AS bonus_total
		FROM `tabSales Invoice` si
		INNER JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
		WHERE si.docstatus = 1
		  AND COALESCE(si.is_return, 0) = 0
		{item_clause}
		GROUP BY COALESCE(NULLIF(si.customer_name, ''), si.customer, 'Unknown Client')
		""",
		item_params,
		as_dict=True,
	)

	return_rows = frappe.db.sql(
		f"""
		SELECT
			COALESCE(NULLIF(customer_name, ''), customer, 'Unknown Client') AS client,
			SUM(ABS(COALESCE(base_net_total, net_total, 0))) AS return_amount,
			SUM(COALESCE(loyalty_amount, 0)) AS loyalty_bonus
		FROM `tabSales Invoice`
		WHERE docstatus = 1
		  AND COALESCE(is_return, 0) = 1
		{invoice_clause}
		GROUP BY COALESCE(NULLIF(customer_name, ''), customer, 'Unknown Client')
		""",
		invoice_params,
		as_dict=True,
	)

	return_map = {
		row.client: {
			"return_amount": flt(row.return_amount),
			"loyalty_bonus": flt(row.loyalty_bonus),
		}
		for row in return_rows
	}

	clients = []
	for row in sales_rows:
		sales_amount = flt(row.sales_amount)
		cost_amount = flt(row.cost_amount)
		margin_amount = sales_amount - cost_amount
		return_amount = flt(return_map.get(row.client, {}).get("return_amount"))
		discount_total = flt(row.discount_total)
		bonus_total = flt(row.bonus_total) + flt(return_map.get(row.client, {}).get("loyalty_bonus"))
		net_margin = margin_amount - discount_total
		clients.append(
			{
				"client": row.client,
				"sales": sales_amount,
				"cost": cost_amount,
				"qty": flt(row.qty_total),
				"returns": return_amount,
				"margin": margin_amount,
				"margin_percent": (margin_amount / sales_amount * 100) if sales_amount else 0,
				"bonus": bonus_total,
				"discount": discount_total,
				"net_margin": net_margin,
				"profitability": (net_margin / sales_amount * 100) if sales_amount else 0,
			}
		)

	return sorted(clients, key=lambda row: row["sales"], reverse=True)


def _build_client_rows(metrics: list[dict[str, Any]]) -> list[list[str | bool]]:
	rows: list[list[str | bool]] = []
	for row in metrics:
		rows.append(
			[
				row["client"],
				format_number(row["sales"]),
				format_number(row["cost"]),
				format_number(row["qty"]),
				format_number(row["returns"]),
				format_number(row["margin"]),
				f"{row['margin_percent']:.1f}%",
				format_number(row["bonus"]),
				format_number(row["discount"]),
				format_number(row["net_margin"]),
				f"{row['profitability']:.1f}%",
			]
		)

	total_sales = sum(row["sales"] for row in metrics)
	total_cost = sum(row["cost"] for row in metrics)
	total_returns = sum(row["returns"] for row in metrics)
	total_margin = sum(row["margin"] for row in metrics)
	total_bonus = sum(row["bonus"] for row in metrics)
	total_discount = sum(row["discount"] for row in metrics)
	total_net_margin = sum(row["net_margin"] for row in metrics)
	total_qty = sum(row["qty"] for row in metrics)

	rows.append(
		[
			"Total",
			format_number(total_sales),
			format_number(total_cost),
			format_number(total_qty),
			format_number(total_returns),
			format_number(total_margin),
			f"{(total_margin / total_sales * 100):.1f}%" if total_sales else "0.0%",
			format_number(total_bonus),
			format_number(total_discount),
			format_number(total_net_margin),
			f"{(total_net_margin / total_sales * 100):.1f}%" if total_sales else "0.0%",
			True,
		]
	)
	return rows


def _build_summary_rows(metrics: list[dict[str, Any]]) -> list[list[str | bool]]:
	total_sales = sum(row["sales"] for row in metrics) or 1
	rows: list[list[str | bool]] = []

	for row in metrics:
		rows.append(
			[
				row["client"],
				format_number(row["sales"]),
				f"{(row['sales'] / total_sales * 100):.1f}%",
				format_number(row["margin"]),
				format_number(row["bonus"]),
				format_number(row["discount"]),
			]
		)

	rows.append(
		[
			"Total",
			format_number(sum(row["sales"] for row in metrics)),
			"100.0%",
			format_number(sum(row["margin"] for row in metrics)),
			format_number(sum(row["bonus"] for row in metrics)),
			format_number(sum(row["discount"] for row in metrics)),
			True,
		]
	)
	return rows


def _build_aggregate_rows(metrics: list[dict[str, Any]]) -> list[list[str | bool]]:
	def summarize(label: str, rows: list[dict[str, Any]], is_total: bool = False) -> list[str | bool]:
		sales_total = sum(row["sales"] for row in rows)
		net_margin = sum(row["net_margin"] for row in rows)
		discount_total = sum(row["discount"] for row in rows)
		result: list[str | bool] = [
			label,
			format_number(sales_total),
			format_number(net_margin),
			format_number(discount_total),
			f"{(net_margin / sales_total * 100):.1f}%" if sales_total else "0.0%",
		]
		if is_total:
			result.append(True)
		return result

	rows = [summarize("All Clients", metrics)]
	rows.append(summarize("Total", metrics, is_total=True))
	return rows


def _build_treemap(metrics: list[dict[str, Any]]) -> list[dict[str, Any]]:
	top_metrics = sorted(
		[row for row in metrics if max(row["net_margin"], 0) > 0],
		key=lambda row: row["net_margin"],
		reverse=True,
	)[:10]
	total_net_margin = sum(max(row["net_margin"], 0) for row in top_metrics)

	if not total_net_margin:
		return []

	return [
		{
			"client_name": row["client"],
			"net_profit_margin_amount": round(max(row["net_margin"], 0)),
			"share": (max(row["net_margin"], 0) / total_net_margin) * 100,
		}
		for row in top_metrics
	]


@frappe.whitelist()
def get_kpi_dashboard_data(year: str | None = None, month: str | None = None):
	default_year, default_month = get_default_period(year)
	available_years = get_dashboard_years()
	selected_year = year if year in available_years else default_year
	selected_month = month if month in MONTH_LABELS else default_month

	monthly_metrics = _get_client_metrics(selected_year, selected_month)
	yearly_metrics = _get_client_metrics(selected_year)

	return {
		"title": "KPI",
		"years": available_years,
		"months": MONTH_LABELS,
		"selected_year": selected_year,
		"selected_month": selected_month,
		"kpi_totals": _get_kpi_totals(selected_year, selected_month),
		"client_rows": _build_client_rows(monthly_metrics),
		"summary_rows": _build_client_rows(yearly_metrics),
		"aggregate_rows": _build_aggregate_rows(yearly_metrics),
		"treemap": _build_treemap(monthly_metrics),
	}
