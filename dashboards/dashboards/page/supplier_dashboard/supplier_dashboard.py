from __future__ import annotations

from typing import Any

import frappe
from frappe.utils import flt, get_first_day, get_last_day, getdate, today

from dashboards.dashboards.dashboard_data import convert_company_currency_amount, convert_to_reporting_currency


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


def _get_period_range() -> tuple[str, str, str]:
	reference_date = _get_reference_date()
	return (
		str(get_first_day(reference_date)),
		str(get_last_day(reference_date)),
		reference_date.strftime("%m.%Y"),
	)


def _get_supplier_invoice_rows(start_date: str, end_date: str) -> list[dict[str, Any]]:
	return frappe.db.sql(
		"""
		SELECT
			pi.supplier,
			COALESCE(NULLIF(pi.supplier_name, ''), pi.supplier) AS supplier_name,
			pi.posting_date,
			pi.currency,
			pi.company,
			SUM(CASE WHEN pi.posting_date < %(start_date)s
				THEN COALESCE(pi.grand_total, 0) ELSE 0 END) AS opening_amount,
			SUM(CASE WHEN pi.posting_date BETWEEN %(start_date)s AND %(end_date)s
				THEN COALESCE(pi.grand_total, 0) ELSE 0 END) AS inflow_amount
		FROM `tabPurchase Invoice` pi
		WHERE pi.docstatus = 1
		  AND COALESCE(pi.is_return, 0) = 0
		GROUP BY pi.supplier, supplier_name, pi.posting_date, pi.currency, pi.company
		""",
		{"start_date": start_date, "end_date": end_date},
		as_dict=True,
	)


def _get_supplier_payment_rows(start_date: str, end_date: str) -> list[dict[str, Any]]:
	return frappe.db.sql(
		"""
		SELECT
			pe.party AS supplier,
			COALESCE(NULLIF(sup.supplier_name, ''), pe.party) AS supplier_name,
			pe.posting_date,
			pe.company,
			SUM(CASE WHEN pe.posting_date < %(start_date)s AND acc.account_type = 'Cash'
				THEN COALESCE(pe.base_received_amount, pe.base_paid_amount, 0) ELSE 0 END) AS opening_cash_amount,
			SUM(CASE WHEN pe.posting_date < %(start_date)s AND acc.account_type = 'Bank'
				THEN COALESCE(pe.base_received_amount, pe.base_paid_amount, 0) ELSE 0 END) AS opening_bank_amount,
			SUM(CASE WHEN pe.posting_date BETWEEN %(start_date)s AND %(end_date)s AND acc.account_type = 'Cash'
				THEN COALESCE(pe.base_received_amount, pe.base_paid_amount, 0) ELSE 0 END) AS cash_payment_amount,
			SUM(CASE WHEN pe.posting_date BETWEEN %(start_date)s AND %(end_date)s AND acc.account_type = 'Bank'
				THEN COALESCE(pe.base_received_amount, pe.base_paid_amount, 0) ELSE 0 END) AS bank_payment_amount
		FROM `tabPayment Entry` pe
		LEFT JOIN `tabSupplier` sup ON sup.name = pe.party
		LEFT JOIN `tabAccount` acc ON acc.name = pe.paid_from
		WHERE pe.docstatus = 1
		  AND pe.payment_type = 'Pay'
		  AND pe.party_type = 'Supplier'
		  AND pe.party IS NOT NULL
		GROUP BY pe.party, supplier_name, pe.posting_date, pe.company
		""",
		{"start_date": start_date, "end_date": end_date},
		as_dict=True,
	)


def _build_supplier_rows(start_date: str, end_date: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
	suppliers: dict[str, dict[str, Any]] = {}

	for row in _get_supplier_invoice_rows(start_date, end_date):
		key = row.supplier
		entry = suppliers.setdefault(
			key,
			{
				"supplier": row.supplier,
				"supplier_name": row.supplier_name,
				"opening_base": 0.0,
				"inflow_base": 0.0,
				"cash_payment_base": 0.0,
				"bank_payment_base": 0.0,
			},
		)
		entry.update({"supplier": row.supplier, "supplier_name": row.supplier_name})
		entry["opening_base"] += convert_to_reporting_currency(row.opening_amount, row.currency, row.posting_date, row.company)
		entry["inflow_base"] += convert_to_reporting_currency(row.inflow_amount, row.currency, row.posting_date, row.company)

	for row in _get_supplier_payment_rows(start_date, end_date):
		key = row.supplier
		entry = suppliers.setdefault(
			key,
			{
				"supplier": row.supplier,
				"supplier_name": row.supplier_name,
				"opening_base": 0.0,
				"inflow_base": 0.0,
				"cash_payment_base": 0.0,
				"bank_payment_base": 0.0,
			},
		)
		entry["cash_payment_base"] += convert_company_currency_amount(row.cash_payment_amount, row.posting_date, row.company)
		entry["bank_payment_base"] += convert_company_currency_amount(row.bank_payment_amount, row.posting_date, row.company)
		entry["opening_base"] -= convert_company_currency_amount(
			flt(row.opening_cash_amount) + flt(row.opening_bank_amount),
			row.posting_date,
			row.company,
		)

	rows = []
	totals = {
		"opening": 0.0,
		"inflow": 0.0,
		"cash_payment": 0.0,
		"bank_payment": 0.0,
		"sum_balance": 0.0,
		"sum_prepayment": 0.0,
		"sum_debt": 0.0,
	}

	for value in suppliers.values():
		balance_base = (
			value["opening_base"]
			+ value["inflow_base"]
			- value["cash_payment_base"]
			- value["bank_payment_base"]
		)
		rentability = (balance_base / value["inflow_base"] * 100) if value["inflow_base"] else 0.0

		if not any(
			flt(number)
			for number in (
				value["opening_base"],
				value["inflow_base"],
				value["cash_payment_base"],
				value["bank_payment_base"],
				balance_base,
			)
		):
			continue

		totals["opening"] += value["opening_base"]
		totals["inflow"] += value["inflow_base"]
		totals["cash_payment"] += value["cash_payment_base"]
		totals["bank_payment"] += value["bank_payment_base"]
		totals["sum_balance"] += balance_base

		if balance_base < 0:
			totals["sum_prepayment"] += abs(balance_base)
		else:
			totals["sum_debt"] += balance_base

		rows.append(
			{
				"supplier_name": value["supplier_name"],
				"opening": round(value["opening_base"]),
				"inflow": round(value["inflow_base"]),
				"cash_payment": round(value["cash_payment_base"]),
				"bank_payment": round(value["bank_payment_base"]),
				"sum_balance": round(balance_base),
				"rentability": rentability,
			}
		)

	rows.sort(key=lambda row: (row["sum_balance"] >= 0, row["sum_balance"], row["supplier_name"]))

	return rows, {key: round(value) for key, value in totals.items()}


@frappe.whitelist()
def get_dashboard_context():
	company_name, company_currency = _get_company_details()
	start_date, end_date, period_label = _get_period_range()
	rows, totals = _build_supplier_rows(start_date, end_date)

	return {
		"company_name": company_name,
		"company_currency": company_currency,
		"period_label": period_label,
		"columns": {
			"local_balance_label": "Сум остаток",
		},
		"kpis": {
			"sum_prepayment": totals["sum_prepayment"],
			"sum_debt": totals["sum_debt"],
		},
		"rows": rows,
		"totals": totals,
	}
