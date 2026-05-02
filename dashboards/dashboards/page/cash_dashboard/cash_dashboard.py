from __future__ import annotations

from typing import Any

import frappe
from frappe.utils import flt, getdate, get_first_day, get_last_day, today

from dashboards.dashboards.dashboard_data import MONTH_LABELS


TAB_ITEMS = [
	{"label": "ГЛАВНЫЙ", "route": "/app/main-dashboard"},
	{"label": "ПАНЕЛЬ", "route": "/app/page-dashboard"},
	{"label": "ЕЖЕДНЕВНО", "route": "/app/daily-dashboard"},
	{"label": "ПРОДАЖА", "route": "/app/sales-dashboard"},
	{"label": "КАССА", "route": "/app/cash-dashboard", "active": 1},
	{"label": "КЛИЕНТ", "route": "/app/client-dashboard"},
	{"label": "ПОСТАВЩИКИ", "route": "/app/supplier-dashboard"},
]

MONTHS = [{"key": label.lower(), "label": label} for label in MONTH_LABELS]
MONTH_MAP = {item["key"]: index + 1 for index, item in enumerate(MONTHS)}
ACCOUNT_TYPE_LABELS = {"Cash": "касса", "Bank": "банк"}


def _get_reference_date():
	row = frappe.db.sql(
		"""
		SELECT MAX(posting_date) AS posting_date
		FROM `tabGL Entry`
		WHERE is_cancelled = 0
		""",
		as_dict=True,
	)[0]
	return getdate(row.posting_date) if row.posting_date else getdate(today())


def _get_default_period() -> tuple[str, str]:
	reference_date = _get_reference_date()
	return str(reference_date.year), MONTH_LABELS[reference_date.month - 1].lower()


def _normalize_filters(month: str | None) -> tuple[str, str]:
	default_year, default_month = _get_default_period()
	selected_month = month if month in MONTH_MAP else default_month
	return default_year, selected_month


def _get_period_range(year: str, month: str) -> tuple[str, str]:
	month_no = MONTH_MAP[month]
	reference_date = getdate(f"{year}-{month_no:02d}-01")
	return str(get_first_day(reference_date)), str(get_last_day(reference_date))


def _get_balance(account_type: str, before_date: str | None = None, end_date: str | None = None) -> float:
	clauses = []
	params: dict[str, Any] = {"account_type": account_type}

	if before_date:
		clauses.append("AND gle.posting_date < %(before_date)s")
		params["before_date"] = before_date

	if end_date:
		clauses.append("AND gle.posting_date <= %(end_date)s")
		params["end_date"] = end_date

	row = frappe.db.sql(
		f"""
		SELECT
			SUM(COALESCE(gle.debit, 0) - COALESCE(gle.credit, 0)) AS balance
		FROM `tabGL Entry` gle
		INNER JOIN `tabAccount` acc ON acc.name = gle.account
		WHERE gle.is_cancelled = 0
		  AND acc.is_group = 0
		  AND acc.account_type = %(account_type)s
		  {' '.join(clauses)}
		""",
		params,
		as_dict=True,
	)[0]
	return flt(row.balance)


def _get_flow_rows(account_type: str, start_date: str, end_date: str) -> list[dict[str, Any]]:
	rows = frappe.db.sql(
		"""
		SELECT
			COALESCE(NULLIF(gle.voucher_type, ''), 'Другое') AS label,
			SUM(COALESCE(gle.debit, 0)) AS inflow,
			SUM(COALESCE(gle.credit, 0)) AS outflow
		FROM `tabGL Entry` gle
		INNER JOIN `tabAccount` acc ON acc.name = gle.account
		WHERE gle.is_cancelled = 0
		  AND acc.is_group = 0
		  AND acc.account_type = %(account_type)s
		  AND gle.posting_date BETWEEN %(start_date)s AND %(end_date)s
		GROUP BY COALESCE(NULLIF(gle.voucher_type, ''), 'Другое')
		ORDER BY (SUM(COALESCE(gle.debit, 0)) + SUM(COALESCE(gle.credit, 0))) DESC, label ASC
		""",
		{
			"account_type": account_type,
			"start_date": start_date,
			"end_date": end_date,
		},
		as_dict=True,
	)

	result = []
	for row in rows:
		result.append(
			{
				"label": row.label,
				"inflow": round(flt(row.inflow)),
				"outflow": round(flt(row.outflow)),
				"level": 0,
				"group": True,
			}
		)

	return result


def _build_section(account_type: str, start_date: str, end_date: str) -> dict[str, Any]:
	rows = _get_flow_rows(account_type, start_date, end_date)
	inflow = sum(flt(row["inflow"]) for row in rows)
	outflow = sum(flt(row["outflow"]) for row in rows)
	start_balance = _get_balance(account_type, before_date=start_date)
	end_balance = start_balance + inflow - outflow

	return {
		"label": ACCOUNT_TYPE_LABELS[account_type],
		"rows": rows,
		"metric": {
			"start": round(start_balance),
			"inflow": round(inflow),
			"outflow": round(outflow),
			"end": round(end_balance),
		},
	}


@frappe.whitelist()
def get_dashboard_context(month: str | None = None):
	selected_year, selected_month = _normalize_filters(month)
	start_date, end_date = _get_period_range(selected_year, selected_month)
	cash = _build_section("Cash", start_date, end_date)
	bank = _build_section("Bank", start_date, end_date)

	return {
		"tabs": TAB_ITEMS,
		"default_filters": {"month": selected_month},
		"months": MONTHS,
		"period_label": f"{MONTH_LABELS[MONTH_MAP[selected_month] - 1]} {selected_year}",
		"cash_rows": cash["rows"],
		"bank_rows": bank["rows"],
		"metrics": {
			"cash": cash["metric"],
			"bank": bank["metric"],
		},
	}
