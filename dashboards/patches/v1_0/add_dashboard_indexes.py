"""Add composite indexes that match the dashboards' hot query patterns.

The dashboard aggregates filter GL Entry by (account, posting_date range) and Sales
Invoice by (docstatus, posting_date range). The stock tables only ship single-column
indexes for these, so the queries could not seek efficiently. These composite indexes
let the closing-balance / period-movement aggregates and the year/month rollups use a
single index seek instead of scanning.

`frappe.db.add_index` is idempotent (it checks for the index first and uses
ADD INDEX IF NOT EXISTS), so re-running is safe.
"""

import frappe

INDEXES = [
    # closing-balance & period-movement aggregates in dashboard_data.py
    ("GL Entry", ["account", "posting_date"], "dashboards_gle_account_posting_date"),
    # docstatus=1 + posting_date year/month rollups and MAX(posting_date) probes
    ("Sales Invoice", ["docstatus", "posting_date"], "dashboards_si_docstatus_posting_date"),
]


def execute():
    for doctype, fields, index_name in INDEXES:
        try:
            frappe.db.add_index(doctype, fields, index_name)
        except Exception:
            # An index is an optimization, never a correctness requirement — don't let a
            # failure (e.g. a lock timeout on a large table) block the rest of migrate.
            frappe.log_error(title=f"dashboards: failed to add index {index_name}")
