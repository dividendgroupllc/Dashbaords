"""Себестоимость проданной продукции по месяцам.

Для каждого товара считается месячная себестоимость единицы и её изменение
к предыдущему месяцу (рост — красный, снижение — зелёный).

Себестоимость единицы = списанная при продаже стоимость (COGS), делённая на
проданное количество. Складские движения принадлежат компонентам, но их
``voucher_detail_no`` указывает на строку Sales Invoice Item, поэтому COGS
сворачивается на продаваемую позицию — это единственный способ получить
себестоимость комплектов (Product Bundle, группа «Сотув махсулотлари»): сами они
не складские, их стоимость складывается из списанных компонентов.

Числитель сверен с главной книгой: помесячные суммы совпадают со списаниями на
счёт «Cost of Goods Sold» до рубля.

Месяцы без продаж не пустуют — в них переносится последнее известное значение
(``carried``), поэтому таблица читается как в Excel-версии отчёта: цена «стоит» до
следующего изменения. По перенесённым ячейкам процент не показывается.
"""

from __future__ import annotations

from typing import Any

import frappe
from frappe.utils import flt, getdate, today

from dashboards.dashboards.dashboard_data import MONTH_LABELS, get_company_currency

SHORT_MONTH_LABELS = [
    "Янв",
    "Фев",
    "Мар",
    "Апр",
    "Май",
    "Июн",
    "Июл",
    "Авг",
    "Сен",
    "Окт",
    "Ноя",
    "Дек",
]

# Ниже этого порога изменение считается отсутствующим — иначе копеечные колебания
# средневзвешенной себестоимости красят всю таблицу.
FLAT_THRESHOLD = 0.05


def get_dashboard_context(
    year: str | int | None = None,
    item_group: str | None = None,
) -> dict[str, Any]:
    years = _get_years()
    selected_year = str(year) if year and str(year) in years else years[-1]
    year_number = int(selected_year)

    rates = _get_sales_rates(year_number)
    item_meta = _get_item_meta(list(rates))

    groups = sorted({item_meta[code]["item_group"] for code in rates if item_meta.get(code)})
    selected_group = str(item_group) if item_group and str(item_group) in groups else None

    last_month = _resolve_last_month(rates, year_number)

    rows = []
    for item_code, item_rates in rates.items():
        meta = item_meta.get(item_code)
        if not meta:
            continue
        if selected_group and meta["item_group"] != selected_group:
            continue

        row = _build_row(meta, item_rates, year_number, last_month)
        if row:
            rows.append(row)

    rows.sort(key=lambda row: str(row["item_name"]).lower())

    return {
        "years": years,
        "selected_year": selected_year,
        "item_groups": groups,
        "selected_item_group": selected_group,
        "months": [
            {
                "index": index + 1,
                "label": SHORT_MONTH_LABELS[index],
                "full": MONTH_LABELS[index],
                "is_active": (index + 1) <= last_month,
            }
            for index in range(12)
        ],
        "last_month": last_month,
        "currency": get_company_currency(),
        "rows": rows,
        "default_filters": {
            "year": selected_year,
            "item_group": selected_group,
        },
    }


def apply_view(
    rows: list[dict[str, Any]], search: str | None = None, sort: str | None = None
) -> list[dict[str, Any]]:
    """Поиск и сортировка — те же, что применяет таблица на экране.

    Повторяет visible_rows() из cost_price_analysis.js: выгрузка в Excel обязана
    отдавать ровно то, что видит пользователь. Меняете правила здесь — меняйте и там.
    """
    needle = (search or "").strip().lower()
    if needle:
        rows = [
            row
            for row in rows
            if needle in str(row["item_name"]).lower() or needle in str(row["item_code"]).lower()
        ]
    else:
        rows = list(rows)

    def by_name(row: dict[str, Any]) -> str:
        return str(row["item_name"]).lower()

    def change(row: dict[str, Any]) -> float:
        return flt(row["year_change"])

    if sort == "rise":
        rows.sort(key=lambda row: (-change(row), by_name(row)))
    elif sort == "fall":
        rows.sort(key=lambda row: (change(row), by_name(row)))
    elif sort == "cost":
        rows.sort(key=lambda row: (-flt(row["avg"]), by_name(row)))
    else:
        rows.sort(key=by_name)

    return rows


# ─────────────────────────────── источники данных ───────────────────────────────


def _get_years() -> list[str]:
    rows = frappe.db.sql(
        """
        SELECT DISTINCT YEAR(posting_date) AS year_value
        FROM `tabSales Invoice`
        WHERE docstatus = 1 AND posting_date IS NOT NULL
        ORDER BY year_value
        """,
        as_dict=True,
    )

    values = [str(row.year_value) for row in rows if row.year_value]
    return values or [str(getdate(today()).year)]


def _date_window(year_number: int) -> dict[str, str]:
    """Окно на два года: предыдущий год нужен как база сравнения для января."""
    return {
        "from_date": f"{year_number - 1}-01-01",
        "to_date": f"{year_number}-12-31",
    }


def _get_sales_rates(year_number: int) -> dict[str, dict[tuple[int, int], float]]:
    params = _date_window(year_number)

    # Списанная стоимость. Для комплектов складские движения принадлежат компонентам,
    # но voucher_detail_no указывает на строку Sales Invoice Item — поэтому COGS
    # сворачивается на продаваемую позицию, а не на компонент.
    #
    # Возвраты исключены из обеих выборок. Возврат не меняет того, во сколько обошёлся
    # товар, а числитель и знаменатель обязаны считаться по одним и тем же строкам:
    # возврат без обратной проводки по складу (а такие в базе есть) уменьшал бы только
    # количество и завышал себестоимость единицы. Так же поступает отчёт Gross Profit.
    cost_rows = frappe.db.sql(
        """
        SELECT
            sii.item_code AS item_code,
            YEAR(si.posting_date) AS year_no,
            MONTH(si.posting_date) AS month_no,
            SUM(-sle.stock_value_difference) AS value
        FROM `tabStock Ledger Entry` sle
        INNER JOIN `tabSales Invoice Item` sii ON sii.name = sle.voucher_detail_no
        INNER JOIN `tabSales Invoice` si ON si.name = sle.voucher_no
        WHERE sle.is_cancelled = 0
          AND sle.voucher_type = 'Sales Invoice'
          AND si.docstatus = 1
          AND COALESCE(si.is_return, 0) = 0
          AND si.posting_date BETWEEN %(from_date)s AND %(to_date)s
        GROUP BY sii.item_code, YEAR(si.posting_date), MONTH(si.posting_date)
        """,
        params,
        as_dict=True,
    )

    qty_rows = frappe.db.sql(
        """
        SELECT
            sii.item_code AS item_code,
            YEAR(si.posting_date) AS year_no,
            MONTH(si.posting_date) AS month_no,
            SUM(COALESCE(sii.stock_qty, sii.qty, 0)) AS qty
        FROM `tabSales Invoice Item` sii
        INNER JOIN `tabSales Invoice` si ON si.name = sii.parent
        WHERE si.docstatus = 1
          AND COALESCE(si.is_return, 0) = 0
          AND si.posting_date BETWEEN %(from_date)s AND %(to_date)s
        GROUP BY sii.item_code, YEAR(si.posting_date), MONTH(si.posting_date)
        """,
        params,
        as_dict=True,
    )

    qty_map: dict[tuple[str, int, int], float] = {}
    for row in qty_rows:
        qty_map[(row.item_code, int(row.year_no), int(row.month_no))] = flt(row.qty)

    merged = []
    for row in cost_rows:
        key = (row.item_code, int(row.year_no), int(row.month_no))
        merged.append(
            frappe._dict(
                {
                    "item_code": row.item_code,
                    "year_no": row.year_no,
                    "month_no": row.month_no,
                    "qty": qty_map.get(key, 0),
                    "value": row.value,
                }
            )
        )

    return _collect_rates(merged)


def _collect_rates(rows) -> dict[str, dict[tuple[int, int], float]]:
    rates: dict[str, dict[tuple[int, int], float]] = {}
    for row in rows:
        qty = flt(row.qty)
        value = flt(row.value)
        if qty <= 0 or value <= 0:
            continue

        rates.setdefault(row.item_code, {})[(int(row.year_no), int(row.month_no))] = value / qty

    return rates


def _get_item_meta(item_codes: list[str]) -> dict[str, dict[str, str]]:
    if not item_codes:
        return {}

    rows = frappe.get_all(
        "Item",
        filters={"name": ["in", item_codes]},
        fields=["name", "item_name", "item_group", "stock_uom"],
        limit_page_length=0,
    )

    return {
        row.name: {
            "item_code": row.name,
            "item_name": row.item_name or row.name,
            "item_group": row.item_group or "",
            "uom": row.stock_uom or "",
        }
        for row in rows
    }


def _resolve_last_month(rates: dict[str, dict[tuple[int, int], float]], year_number: int) -> int:
    """Последний месяц выбранного года, в котором вообще есть данные.

    Месяцы после него остаются пустыми: переносить в них последнюю известную цену
    значило бы показывать себестоимость за периоды, которых ещё не было."""
    months = [
        month
        for item_rates in rates.values()
        for (row_year, month) in item_rates
        if row_year == year_number
    ]
    return max(months) if months else 0


# ──────────────────────────────── сборка строк ────────────────────────────────


def _build_row(
    meta: dict[str, str],
    item_rates: dict[tuple[int, int], float],
    year_number: int,
    last_month: int,
) -> dict[str, Any] | None:
    if not any(row_year == year_number for (row_year, _month) in item_rates):
        return None

    # База сравнения для января — последнее известное значение предыдущего года.
    previous: float | None = None
    for month in range(1, 13):
        carry = item_rates.get((year_number - 1, month))
        if carry:
            previous = carry

    cells: list[dict[str, Any] | None] = []
    for month in range(1, 13):
        if month > last_month:
            cells.append(None)
            continue

        raw = item_rates.get((year_number, month))
        if raw:
            value, carried = raw, False
        elif previous is not None:
            value, carried = previous, True
        else:
            cells.append(None)
            continue

        change = None
        if raw is not None and previous:
            change = (raw - previous) / previous * 100

        cells.append(_make_cell(value, change, carried))
        previous = value

    _backfill_leading(cells)

    values = [cell["value"] for cell in cells if cell]
    if not values:
        return None

    first_value = values[0]
    last_value = values[-1]
    year_change = ((last_value - first_value) / first_value * 100) if first_value else None

    return {
        "item_code": meta["item_code"],
        "item_name": meta["item_name"],
        "item_group": meta["item_group"],
        "uom": meta["uom"],
        "cells": cells,
        # В таблицу не выводятся — питают сортировку «Цена» / «Рост» / «Снижение».
        "avg": sum(values) / len(values),
        "year_change": year_change,
    }


def _make_cell(value: float, change: float | None, carried: bool) -> dict[str, Any]:
    return {
        "value": value,
        "display": _format_money(value),
        "change": change,
        "change_display": _format_percent(change),
        "direction": _direction(change),
        "carried": carried,
    }


def _backfill_leading(cells: list[dict[str, Any] | None]) -> None:
    """Месяцы до первого прихода заполняются первой известной ценой.

    Без этого таблица начинается с дыр там, где товар просто не двигался в начале
    года; значения помечены как перенесённые и процент по ним не показывается."""
    first_index = next((index for index, cell in enumerate(cells) if cell), None)
    if first_index in (None, 0):
        return

    first_cell = cells[first_index]
    for index in range(first_index):
        cells[index] = _make_cell(first_cell["value"], None, True)


# ──────────────────────────────── форматирование ────────────────────────────────


def _format_money(value: float | None) -> str:
    if value is None:
        return ""

    number = flt(value)
    precision = 0 if abs(number) >= 1000 else 2
    return f"{number:,.{precision}f}".replace(",", " ").replace(".", ",")


def _format_percent(value: float | None) -> str:
    if value is None:
        return ""

    if abs(value) < FLAT_THRESHOLD:
        return "0%"

    sign = "+" if value > 0 else "−"
    return f"{sign}{abs(value):.1f}".replace(".", ",") + "%"


def _direction(value: float | None) -> str:
    if value is None:
        return "none"
    if value > FLAT_THRESHOLD:
        return "up"
    if value < -FLAT_THRESHOLD:
        return "down"
    return "flat"
