from __future__ import annotations

from typing import Any

import frappe
from frappe.utils import flt, get_first_day, get_last_day, getdate, today

from dashboards.dashboards.dashboard_data import convert_company_currency_amount, convert_to_reporting_currency
from dashboards.dashboards.dashboard_data import MONTH_LABELS


def _get_company_details() -> tuple[str, str]:
	company = (
		frappe.defaults.get_user_default("Company")
		or frappe.defaults.get_global_default("company")
		or frappe.db.get_value("Company", {}, "name")
	)
	if not company:
		return "Компания", "UZS"

	return company, "UZS"


def _get_reference_date():
	purchase_row = frappe.db.sql(
		"""
		SELECT MAX(posting_date) AS posting_date
		FROM `tabPurchase Invoice`
		WHERE docstatus = 1
		  AND COALESCE(is_return, 0) = 0
		""",
		as_dict=True,
	)[0]
	payment_row = frappe.db.sql(
		"""
		SELECT MAX(posting_date) AS posting_date
		FROM `tabPayment Entry`
		WHERE docstatus = 1
		  AND payment_type = 'Pay'
		  AND party_type = 'Supplier'
		""",
		as_dict=True,
	)[0]

	dates = [value for value in (purchase_row.posting_date, payment_row.posting_date) if value]
	if not dates:
		return getdate(today())

	return max(getdate(value) for value in dates)


def _get_years() -> list[str]:
	rows = frappe.db.sql(
		"""
		SELECT year_value
		FROM (
			SELECT DISTINCT YEAR(posting_date) AS year_value
			FROM `tabPurchase Invoice`
			WHERE docstatus = 1
			  AND COALESCE(is_return, 0) = 0
			  AND posting_date IS NOT NULL
			UNION
			SELECT DISTINCT YEAR(posting_date) AS year_value
			FROM `tabPayment Entry`
			WHERE docstatus = 1
			  AND payment_type = 'Pay'
			  AND party_type = 'Supplier'
			  AND posting_date IS NOT NULL
		) years
		WHERE year_value IS NOT NULL
		ORDER BY year_value
		""",
		as_dict=True,
	)
	values = [str(row.year_value) for row in rows if row.year_value]
	if values:
		return values
	return [str(getdate(today()).year)]


def _get_default_period() -> tuple[str, str]:
	reference_date = _get_reference_date()
	return str(reference_date.year), MONTH_LABELS[reference_date.month - 1]


def _normalize_filters(year: str | None, month: str | None) -> tuple[str, str | None]:
	years = _get_years()
	default_year, default_month = _get_default_period()
	selected_year = str(year) if str(year) in years else default_year
	selected_month = month if month in MONTH_LABELS else default_month
	return selected_year, selected_month


def _get_period_range(year: str, month: str | None) -> tuple[str, str, str]:
	if month in MONTH_LABELS:
		month_index = MONTH_LABELS.index(month) + 1
		reference_date = getdate(f"{year}-{month_index:02d}-01")
		return str(get_first_day(reference_date)), str(get_last_day(reference_date)), f"{month} {year}"

	return f"{year}-01-01", f"{year}-12-31", year


def _party_dashboard_config(view: str) -> dict[str, str]:
	if view == "client":
		return {
			"party_type": "Customer",
			"party_field": "customer",
			"payment_party_field": "party",
			"name_field": "customer_name",
			"party_title": "Клиент",
			"party_title_plural": "Клиенты",
			"invoice_label": "Продажа",
			"invoice_table": "tabSales Invoice",
			"invoice_item_table": "tabSales Invoice Item",
			"payment_amount_field": "paid_amount",
			"payment_currency_field": "paid_from_account_currency",
			"payment_account_field": "paid_to",
			"payment_type": "Receive",
			"payment_party_table": "tabCustomer",
			"payment_party_name_field": "customer_name",
			"unknown_party": "Неизвестный клиент",
		}

	return {
		"party_type": "Supplier",
		"party_field": "supplier",
		"payment_party_field": "party",
		"name_field": "supplier_name",
		"party_title": "Поставщик",
		"party_title_plural": "Поставщики",
		"invoice_label": "Приход",
		"invoice_table": "tabPurchase Invoice",
		"invoice_item_table": "tabPurchase Invoice Item",
		"payment_amount_field": "received_amount",
		"payment_currency_field": "paid_to_account_currency",
		"payment_account_field": "paid_from",
		"payment_type": "Pay",
		"payment_party_table": "tabSupplier",
		"payment_party_name_field": "supplier_name",
		"unknown_party": "Неизвестный поставщик",
	}


def _party_filter_clause(view: str, party: str | None, params: dict[str, Any], alias: str) -> str:
	if not party:
		return ""
	config = _party_dashboard_config(view)
	params["party"] = party
	field = config["payment_party_field"] if alias == "pe" else config["party_field"]
	return f" AND {alias}.{field} = %(party)s"


def _get_party_invoice_rows(view: str, start_date: str, end_date: str, party: str | None = None) -> list[dict[str, Any]]:
	config = _party_dashboard_config(view)
	params = {"start_date": start_date, "end_date": end_date}
	party_clause = _party_filter_clause(view, party, params, "doc")

	return frappe.db.sql(
		f"""
		SELECT
			doc.{config['party_field']} AS party,
			COALESCE(NULLIF(doc.{config['name_field']}, ''), doc.{config['party_field']}, '{config['party_title_plural']}') AS party_name,
			doc.posting_date,
			doc.currency,
			doc.company,
			SUM(CASE WHEN doc.posting_date < %(start_date)s THEN COALESCE(doc.grand_total, 0) ELSE 0 END) AS opening_amount,
			SUM(CASE WHEN doc.posting_date BETWEEN %(start_date)s AND %(end_date)s THEN COALESCE(doc.grand_total, 0) ELSE 0 END) AS inflow_amount,
			SUM(CASE WHEN doc.posting_date < %(start_date)s THEN COALESCE(item.stock_qty, item.qty, 0) ELSE 0 END) AS opening_kg,
			SUM(CASE WHEN doc.posting_date BETWEEN %(start_date)s AND %(end_date)s THEN COALESCE(item.stock_qty, item.qty, 0) ELSE 0 END) AS inflow_kg
		FROM `{config['invoice_table']}` doc
		INNER JOIN `{config['invoice_item_table']}` item ON item.parent = doc.name
		WHERE doc.docstatus = 1
		  AND COALESCE(doc.is_return, 0) = 0
		  {party_clause}
		GROUP BY doc.{config['party_field']}, party_name, doc.posting_date, doc.currency, doc.company
		""",
		params,
		as_dict=True,
	)


def _get_party_payment_rows(view: str, start_date: str, end_date: str, party: str | None = None) -> list[dict[str, Any]]:
	config = _party_dashboard_config(view)
	params = {"start_date": start_date, "end_date": end_date}
	party_clause = _party_filter_clause(view, party, params, "pe")

	return frappe.db.sql(
		f"""
		SELECT
			pe.party AS party,
			COALESCE(NULLIF(party.{config['payment_party_name_field']}, ''), pe.party, '{config['unknown_party']}') AS party_name,
			pe.posting_date,
			pe.{config['payment_currency_field']} AS currency,
			pe.company,
			SUM(CASE WHEN pe.posting_date < %(start_date)s AND acc.account_type = 'Cash'
				THEN COALESCE(pe.{config['payment_amount_field']}, 0) ELSE 0 END) AS opening_cash_amount,
			SUM(CASE WHEN pe.posting_date < %(start_date)s AND acc.account_type = 'Bank'
				THEN COALESCE(pe.{config['payment_amount_field']}, 0) ELSE 0 END) AS opening_bank_amount,
			SUM(CASE WHEN pe.posting_date BETWEEN %(start_date)s AND %(end_date)s AND acc.account_type = 'Cash'
				THEN COALESCE(pe.{config['payment_amount_field']}, 0) ELSE 0 END) AS cash_payment_amount,
			SUM(CASE WHEN pe.posting_date BETWEEN %(start_date)s AND %(end_date)s AND acc.account_type = 'Bank'
				THEN COALESCE(pe.{config['payment_amount_field']}, 0) ELSE 0 END) AS bank_payment_amount
		FROM `tabPayment Entry` pe
		LEFT JOIN `{config['payment_party_table']}` party ON party.name = pe.party
		LEFT JOIN `tabAccount` acc ON acc.name = pe.{config['payment_account_field']}
		WHERE pe.docstatus = 1
		  AND pe.payment_type = %(payment_type)s
		  AND pe.party_type = %(party_type)s
		  AND pe.party IS NOT NULL
		  {party_clause}
		GROUP BY pe.party, party_name, pe.posting_date, pe.{config['payment_currency_field']}, pe.company
		""",
		{
			**params,
			"party_type": config["party_type"],
			"payment_type": config["payment_type"],
		},
		as_dict=True,
	)


def _build_party_rows(view: str, start_date: str, end_date: str, party: str | None = None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
	rows_by_key: dict[tuple[str, str], dict[str, Any]] = {}
	totals = {
		"opening": 0.0,
		"inflow": 0.0,
		"cash_payment": 0.0,
		"bank_payment": 0.0,
		"sum_balance": 0.0,
		"sum_prepayment": 0.0,
		"sum_debt": 0.0,
		"kg": 0.0,
	}

	for row in _get_party_invoice_rows(view, start_date, end_date, party=party):
		key = (str(row.party), str(row.currency or "UZS"))
		entry = rows_by_key.setdefault(
			key,
			{
				"party": row.party,
				"party_name": row.party_name,
				"currency": row.currency or "UZS",
				"opening": 0.0,
				"inflow": 0.0,
				"kg": 0.0,
				"cash_payment": 0.0,
				"bank_payment": 0.0,
				"opening_base": 0.0,
				"inflow_base": 0.0,
				"cash_payment_base": 0.0,
				"bank_payment_base": 0.0,
			},
		)
		entry["party_name"] = row.party_name
		entry["opening"] += flt(row.opening_amount)
		entry["inflow"] += flt(row.inflow_amount)
		entry["kg"] += flt(row.inflow_kg)
		entry["opening_base"] += convert_to_reporting_currency(row.opening_amount, row.currency, row.posting_date, row.company)
		entry["inflow_base"] += convert_to_reporting_currency(row.inflow_amount, row.currency, row.posting_date, row.company)

	for row in _get_party_payment_rows(view, start_date, end_date, party=party):
		key = (str(row.party), str(row.currency or "UZS"))
		entry = rows_by_key.setdefault(
			key,
			{
				"party": row.party,
				"party_name": row.party_name,
				"currency": row.currency or "UZS",
				"opening": 0.0,
				"inflow": 0.0,
				"kg": 0.0,
				"cash_payment": 0.0,
				"bank_payment": 0.0,
				"opening_base": 0.0,
				"inflow_base": 0.0,
				"cash_payment_base": 0.0,
				"bank_payment_base": 0.0,
			},
		)
		entry["party_name"] = row.party_name
		opening_payment = flt(row.opening_cash_amount) + flt(row.opening_bank_amount)
		period_cash = flt(row.cash_payment_amount)
		period_bank = flt(row.bank_payment_amount)

		entry["opening"] -= opening_payment
		entry["cash_payment"] += period_cash
		entry["bank_payment"] += period_bank
		entry["opening_base"] -= convert_to_reporting_currency(opening_payment, row.currency, row.posting_date, row.company)
		entry["cash_payment_base"] += convert_to_reporting_currency(period_cash, row.currency, row.posting_date, row.company)
		entry["bank_payment_base"] += convert_to_reporting_currency(period_bank, row.currency, row.posting_date, row.company)

	rows = []
	for value in rows_by_key.values():
		balance = value["opening"] + value["inflow"] - value["cash_payment"] - value["bank_payment"]
		balance_base = value["opening_base"] + value["inflow_base"] - value["cash_payment_base"] - value["bank_payment_base"]

		if not any(
			flt(number)
			for number in (
				value["opening"],
				value["inflow"],
				value["cash_payment"],
				value["bank_payment"],
				value["kg"],
				balance,
			)
		):
			continue

		totals["opening"] += value["opening_base"]
		totals["inflow"] += value["inflow_base"]
		totals["cash_payment"] += value["cash_payment_base"]
		totals["bank_payment"] += value["bank_payment_base"]
		totals["sum_balance"] += balance_base
		totals["kg"] += value["kg"]

		if balance_base < 0:
			totals["sum_prepayment"] += abs(balance_base)
		else:
			totals["sum_debt"] += balance_base

		rows.append(
			{
				"party": value["party"],
				"party_name": value["party_name"],
				"currency": value["currency"],
				"opening": round(value["opening"]),
				"inflow": round(value["inflow"]),
				"kg": round(value["kg"], 2),
				"cash_payment": round(value["cash_payment"]),
				"bank_payment": round(value["bank_payment"]),
				"sum_balance": round(balance),
			}
		)

	rows.sort(key=lambda row: (row["sum_balance"] >= 0, row["sum_balance"], row["party_name"]))

	return rows, {key: round(value, 2) if key == "kg" else round(value) for key, value in totals.items()}


@frappe.whitelist()
def get_dashboard_context(year: str | None = None, month: str | None = None, view: str | None = None, party: str | None = None):
	company_name, company_currency = _get_company_details()
	selected_year, selected_month = _normalize_filters(year, month)
	start_date, end_date, period_label = _get_period_range(selected_year, selected_month)
	selected_view = view if view in {"client", "supplier"} else "supplier"
	config = _party_dashboard_config(selected_view)
	rows, totals = _build_party_rows(selected_view, start_date, end_date, party=party)
	selected_party_name = next((row["party_name"] for row in rows if row["party"] == party), None) if party else None

	return {
		"company_name": company_name,
		"company_currency": company_currency,
		"period_label": period_label,
		"years": _get_years(),
		"months": MONTH_LABELS,
		"view": selected_view,
		"view_label": config["party_title_plural"],
		"default_filters": {
			"year": selected_year,
			"month": selected_month,
			"view": selected_view,
			"party": party,
		},
		"selected_party_name": selected_party_name,
		"columns": {
			"party_label": config["party_title"],
			"inflow_label": config["invoice_label"],
			"currency_label": "Валюта",
			"kg_label": "KG",
			"cash_payment_label": "Оплата наличными",
			"bank_payment_label": "Оплата банком",
			"balance_label": "Сум остаток",
		},
		"kpis": {
			"sum_prepayment": totals["sum_prepayment"],
			"sum_debt": totals["sum_debt"],
		},
		"rows": rows,
		"totals": totals,
	}
