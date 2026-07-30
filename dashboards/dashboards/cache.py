"""Cross-request Redis caching for dashboard entrypoints.

Every dashboard open used to recompute dozens of SQL aggregates and several full
ERPNext report executions from scratch. This module adds a thin Redis layer on top
of the whitelisted entrypoints so the assembled payload is served from cache, keyed
by (dashboard, company, call args).

Freshness is event-driven: `on_ledger_change` (wired in hooks.doc_events) clears the
cache whenever a Sales Invoice / Payment Entry / Journal Entry / Stock Ledger Entry is
submitted or cancelled, so dashboards reflect new documents on the next open. The TTL
is only a safety backstop in case an invalidation is ever missed.
"""

from __future__ import annotations

import functools
import inspect
from typing import Callable

import frappe
from frappe.utils import cint

# Event invalidation is the primary freshness mechanism; this TTL is just a backstop.
DASHBOARD_CACHE_TTL = 6 * 60 * 60  # 6 hours
CACHE_PREFIX = "dashboard"


def _is_disabled() -> bool:
    return bool(frappe.flags.get("disable_dashboard_cache") or frappe.conf.get("disable_dashboard_cache"))


def _resolve_company() -> str:
    """Resolve the company the dashboards implicitly report on, so cached payloads
    never bleed across companies in a multi-company site."""
    company = (
        frappe.defaults.get_user_default("Company")
        or frappe.defaults.get_global_default("company")
        or frappe.db.get_default("company")
    )
    return str(company or "_")


def _build_key(name: str, key_args: dict) -> str:
    parts = [CACHE_PREFIX, name, _resolve_company()]
    for arg_name in sorted(key_args):
        parts.append(f"{arg_name}={key_args[arg_name]}")
    return "|".join(parts)


def reset_inner_caches() -> None:
    """Clear the process-global module caches in ``dashboard_data`` that persist across
    requests. They are reset on every cache miss so a post-invalidation recompute never
    reuses stale figures, regardless of which worker serves the miss."""
    from dashboards.dashboards import dashboard_data

    dashboard_data._MONTHLY_SALES_PL_CACHE.clear()
    dashboard_data._MONTHLY_NET_PROFIT_PL_CACHE.clear()
    dashboard_data._PL_REPORT_CACHE.clear()


def dashboard_cache(name: str, ttl: int = DASHBOARD_CACHE_TTL) -> Callable:
    """Cache a whitelisted dashboard entrypoint's full payload in Redis.

    The key is ``dashboard|<name>|<company>|<sorted call args>``. The cache is shared
    across gunicorn workers, so the second open of any period — by any user — is served
    without touching the database.

    Pass ``force_refresh=1`` to bypass the read and repopulate. Because Frappe filters
    HTTP kwargs to the wrapped function's real signature (which has no ``force_refresh``
    parameter), this flag is only reachable from internal Python calls such as the
    scheduled warmer — web clients cannot trigger recomputes.
    """

    def decorator(fn: Callable) -> Callable:
        signature = inspect.signature(fn)

        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            if _is_disabled():
                return fn(*args, **kwargs)

            force = cint(kwargs.pop("force_refresh", 0))

            bound = signature.bind_partial(*args, **kwargs)
            bound.apply_defaults()
            key = _build_key(name, dict(bound.arguments))

            cache = frappe.cache()
            if not force:
                # expires=True reads straight from Redis without caching the result (or a
                # miss) in the request-local store, which would otherwise shadow the value
                # written by set_value() with an expiry within the same process.
                cached = cache.get_value(key, expires=True)
                if cached is not None:
                    return cached

            # Reached only on a miss: ensure the recompute starts from clean inner caches.
            reset_inner_caches()
            result = fn(*args, **kwargs)
            cache.set_value(key, result, expires_in_sec=ttl)
            return result

        wrapper.__dashboard_cache_name__ = name
        return wrapper

    return decorator


def clear_dashboard_cache(name: str | None = None) -> None:
    """Delete cached dashboard payloads. Clears one dashboard when ``name`` is given,
    otherwise every dashboard."""
    pattern = f"{CACHE_PREFIX}|{name}|" if name else f"{CACHE_PREFIX}|"
    try:
        frappe.cache().delete_keys(pattern)
    except Exception:
        frappe.log_error(title="Dashboard cache clear failed")


def on_ledger_change(doc=None, method: str | None = None) -> None:
    """doc_events handler: invalidate dashboard caches when ledger-affecting documents
    are submitted or cancelled. Must never raise — invalidation must not block the
    submission of the underlying document."""
    try:
        clear_dashboard_cache()
        reset_inner_caches()
    except Exception:
        frappe.log_error(title="Dashboard cache invalidation failed")


# Entrypoints warmed by the scheduler. Each is called with no period args, which resolves
# to the default (latest) period — exactly the key a user's first open hits.
WARM_TARGETS = [
    "dashboards.dashboards.page.main_dashboard.main_dashboard.get_dashboard_data",
    "dashboards.dashboards.page.page_dashboard.page_dashboard.get_dashboard_context",
    "dashboards.dashboards.page.daily_dashboard.daily_dashboard.get_dashboard_context",
    "dashboards.dashboards.page.sales_dashboard.sales_dashboard.get_dashboard_context",
    "dashboards.dashboards.page.manufacture_dashboard.manufacture_dashboard.get_dashboard_data",
    "dashboards.dashboards.page.cost_price_analysis.cost_price_analysis.get_dashboard_context",
    "dashboards.dashboards.page.supplier_dashboard.supplier_dashboard.get_dashboard_context",
    "dashboards.dashboards.page.monthly_analysis.monthly_analysis.get_dashboard_context",
    "dashboards.dashboards.page.comparison_by_amount.comparison_by_amount.get_dashboard_context",
    "dashboards.dashboards.page.comparison_by_weight.comparison_by_weight.get_dashboard_context",
    "dashboards.dashboards.page.comparison_by_product.comparison_by_product.get_dashboard_context",
    "dashboards.dashboards.page.product_comparison.product_comparison.get_dashboard_context",
    "dashboards.dashboards.page.customer_comparison.customer_comparison.get_dashboard_context",
    "dashboards.dashboards.page.product_by_customer.product_by_customer.get_dashboard_context",
    "dashboards.dashboards.page.dividend_analysis.dividend_analysis.get_dashboard_context",
    "dashboards.dashboards.page.investors.investors.get_dashboard_data",
]


def warm_current_period() -> None:
    """Scheduled (hourly) cache warmer: recompute each dashboard's default-period payload
    and store it in Redis, so the next user open is served warm even right after a TTL
    expiry or an event invalidation. A failure in one dashboard is logged, never raised,
    so it can't stop the others or fail the scheduler job."""
    for method_path in WARM_TARGETS:
        try:
            frappe.get_attr(method_path)(force_refresh=1)
        except Exception:
            frappe.log_error(title=f"Dashboard cache warm failed: {method_path}")
