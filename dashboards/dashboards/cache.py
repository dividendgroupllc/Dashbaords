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
import time
from typing import Callable

import frappe
from frappe.utils import cint, flt

# --- Yangilik siyosati (2026-10-29 da qayta qurildi) --------------------------
#
# Avvalgi model: hujjat o'zgarsa kesh O'CHIRILARDI, keyingi ochuvchi esa noldan
# hisoblardi. O'lchandi: page_dashboard sovuq holatda 29 s, main_dashboard 12 s,
# va kesh kuniga ~272 marta o'chardi (Stock Ledger Entry qator darajasida
# ulangan edi) — ya'ni foydalanuvchi deyarli HAR ochishda to'liq hisobni
# kutardi. Kesh bor edi, lekin amalda hech qachon ishlamasdi.
#
# Yangi model — «eski bo'lsa ham darhol ber, fonda yangila»
# (stale-while-revalidate):
#   * SOFT muddatdan keyin (yoki hujjat o'zgarganda) yozuv «eskirgan» deb
#     belgilanadi, lekin O'CHIRILMAYDI;
#   * foydalanuvchi eskirgan yozuvni DARHOL oladi, yangilash esa fon ishiga
#     (worker) topshiriladi — kutish yo'q;
#   * HARD muddatdan keyin (yoki yozuv umuman bo'lmasa) eski xatti-harakat:
#     joyida hisoblanadi. Ya'ni eng yomon holat avvalgidan yomon emas.
#
# Eskirganlikni belgilash O(1): hujjat o'zgarganda bitta «stale epoch»
# vaqt belgisi yoziladi, undan OLDIN yozilgan hamma yozuv eskirgan hisoblanadi.
# Kalitlarni skanlash yoki o'chirish kerak emas.
DASHBOARD_CACHE_SOFT_TTL = 10 * 60           # 10 daqiqa: shundan keyin fonda yangilanadi
DASHBOARD_CACHE_STALE_MAX = 2 * 60 * 60      # 2 soat: bundan eski bo'lsa joyida hisoblanadi
DASHBOARD_CACHE_HARD_TTL = 7 * 24 * 60 * 60  # 7 kun: Redis'da saqlanish muddati
DASHBOARD_CACHE_TTL = DASHBOARD_CACHE_SOFT_TTL  # orqaga moslik uchun nom
CACHE_PREFIX = "dashboard"
STALE_EPOCH_KEY = "dashboard|__stale_epoch"


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


def _now() -> float:
    return time.time()


def stale_epoch() -> float:
    """Shu vaqtdan OLDIN yozilgan kesh yozuvlari eskirgan hisoblanadi."""
    try:
        return float(frappe.cache().get_value(STALE_EPOCH_KEY, expires=True) or 0)
    except Exception:
        return 0.0


def bump_stale_epoch() -> None:
    """Hujjat o'zgardi — hamma yozuvni bir harakatda «eskirgan» qilish."""
    frappe.cache().set_value(STALE_EPOCH_KEY, _now(), expires_in_sec=DASHBOARD_CACHE_HARD_TTL)


# --- Davr kesimida eskirganlik -----------------------------------------------
#
# Gross Profit hisoboti davr bo'yicha hisoblanadi, YOPILGAN oy esa o'zgarmaydi:
# 2026-yil yanvaridagi tannarx bugun yangi schyot kiritilgani uchun o'zgarmaydi.
# Shuning uchun global «stale epoch» bu yerda juda qo'pol — u 10 oylik
# yopilgan hisobni ham bekor qilib yuborardi. Bu yerda eskirganlik OY
# kesimida yuritiladi: faqat hujjat tushgan oy (va uni qamrab olgan
# diapazonlar) qayta hisoblanadi.
PERIOD_STALE_PREFIX = "dashboard|gp_stale|"


def _month_keys(from_date, to_date) -> list[str]:
    """[from, to] oraliqdagi oylar ro'yxati: ['2026-01', '2026-02', ...]."""
    from frappe.utils import add_months, get_first_day, getdate

    boshi, oxiri = getdate(from_date), getdate(to_date)
    if boshi > oxiri:
        return []
    kun, oylar = get_first_day(boshi), []
    oxirgi = get_first_day(oxiri)
    while kun <= oxirgi and len(oylar) <= 240:
        oylar.append(kun.strftime("%Y-%m"))
        kun = get_first_day(add_months(kun, 1))
    return oylar


def bump_period_stale(posting_date=None) -> None:
    """Hujjat tushgan oyni (sanasi noma'lum bo'lsa — hammasini) eskirgan qiladi."""
    cache = frappe.cache()
    if not posting_date:
        # Sana noma'lum: global epoch allaqachon ko'tarilgan, davr keshini
        # butunlay tashlashdan ko'ra joriy oyni belgilaymiz va qolganini
        # HARD muddatga qoldiramiz — yopilgan oylar behuda qayta hisoblanmasin.
        posting_date = frappe.utils.nowdate()
    try:
        kalit = PERIOD_STALE_PREFIX + frappe.utils.getdate(posting_date).strftime("%Y-%m")
    except Exception:
        return
    cache.set_value(kalit, _now(), expires_in_sec=DASHBOARD_CACHE_HARD_TTL)


def period_stale_epoch(from_date, to_date) -> float:
    """Diapazonni qamrab olgan oylarning eng YANGI eskirish vaqti."""
    cache = frappe.cache()
    eng_yangi = 0.0
    for oy in _month_keys(from_date, to_date):
        try:
            v = flt(cache.get_value(PERIOD_STALE_PREFIX + oy, expires=True) or 0)
        except Exception:
            v = 0.0
        if v > eng_yangi:
            eng_yangi = v
    return eng_yangi


def _enqueue_refresh(method_path: str, kwargs: dict) -> None:
    """Fonda qayta hisoblashni navbatga qo'yadi.

    `job_id` bir xil bo'lgani uchun bir vaqtda bitta xuddi shu ish turadi:
    bir nechta foydalanuvchi bir vaqtda eskirgan sahifani ochsa ham qayta
    hisob BIR marta bajariladi (dedupe).
    """
    try:
        frappe.enqueue(
            "dashboards.dashboards.cache.refresh_entry",
            queue="long",
            timeout=1800,
            job_id=f"dashboard-refresh::{method_path}::{sorted(kwargs.items())}",
            deduplicate=True,
            method_path=method_path,
            call_kwargs=kwargs,
        )
    except Exception:
        # Navbat ishlamasa ham foydalanuvchi eskirgan qiymatni oladi —
        # HARD muddat tugagach joyida qayta hisoblanadi.
        frappe.log_error(title="Dashboard cache refresh enqueue failed")


def refresh_entry(method_path: str, call_kwargs: dict | None = None) -> None:
    """Fon ishi: bitta kesh yozuvini qayta hisoblab yozadi."""
    frappe.get_attr(method_path)(force_refresh=1, **(call_kwargs or {}))


def reset_inner_caches() -> None:
    """Clear the process-global module caches in ``dashboard_data`` that persist across
    requests. They are reset on every cache miss so a post-invalidation recompute never
    reuses stale figures, regardless of which worker serves the miss."""
    from dashboards.dashboards import dashboard_data

    dashboard_data._MONTHLY_SALES_PL_CACHE.clear()
    dashboard_data._MONTHLY_NET_PROFIT_PL_CACHE.clear()
    dashboard_data._PL_REPORT_CACHE.clear()
    # so'rov doirasidagi Gross Profit keshi ham tozalanadi (2026-10-29)
    dashboard_data._gross_profit_request_cache().clear()


def dashboard_cache(name: str, ttl: int = DASHBOARD_CACHE_SOFT_TTL) -> Callable:
    """Cache a whitelisted dashboard entrypoint's full payload in Redis.

    The key is ``dashboard|<name>|<company>|<sorted call args>``. The cache is shared
    across gunicorn workers, so the second open of any period — by any user — is served
    without touching the database.

    UCH HOLAT (2026-10-29):
      * yozuv bor va YANGI  -> darhol qaytariladi;
      * yozuv bor, lekin ESKIRGAN (soft muddat o'tgan yoki hujjat o'zgargan)
        -> darhol SHU yozuv qaytariladi, yangilash fon ishiga topshiriladi.
        Foydalanuvchi kutmaydi; keyingi ochishda yangi raqam turadi;
      * yozuv yo'q, yoki yoshi STALE_MAX (2 soat) dan oshgan -> joyida
        hisoblanadi (avvalgi xatti-harakat). Ya'ni fon ishi biror sababdan
        bajarilmasa ham ma'lumot 2 soatdan ko'p eskirmaydi, va eng yomon
        holat avvalgisidan yomon emas.

    Pass ``force_refresh=1`` to bypass the read and repopulate. Because Frappe filters
    HTTP kwargs to the wrapped function's real signature (which has no ``force_refresh``
    parameter), this flag is only reachable from internal Python calls such as the
    scheduled warmer and the background refresh job — web clients cannot trigger
    recomputes.
    """

    def decorator(fn: Callable) -> Callable:
        signature = inspect.signature(fn)
        method_path = f"{fn.__module__}.{fn.__name__}"

        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            if _is_disabled():
                return fn(*args, **kwargs)

            force = cint(kwargs.pop("force_refresh", 0))

            bound = signature.bind_partial(*args, **kwargs)
            bound.apply_defaults()
            call_args = dict(bound.arguments)
            key = _build_key(name, call_args)

            cache = frappe.cache()
            if not force:
                # expires=True reads straight from Redis without caching the result (or a
                # miss) in the request-local store, which would otherwise shadow the value
                # written by set_value() with an expiry within the same process.
                cached = cache.get_value(key, expires=True)
                if isinstance(cached, dict) and "__v" in cached:
                    yozilgan = flt(cached.get("__t"))
                    yosh = _now() - yozilgan
                    eskirgan = yosh >= ttl or yozilgan <= stale_epoch()
                    if not eskirgan:
                        return cached["__v"]
                    if yosh < DASHBOARD_CACHE_STALE_MAX:
                        # Eski, lekin qabul qilinadigan darajada: darhol beramiz
                        # va fonda yangilaymiz.
                        _enqueue_refresh(method_path, call_args)
                        return cached["__v"]
                    # STALE_MAX dan ham oshgan: demak fon ishi bajarilmayapti
                    # (worker ishlamayotgandir). Bunday holatda eski raqamni
                    # cheksiz ko'rsatishdan ko'ra foydalanuvchini kutdirib,
                    # TO'G'RI raqamni berish xavfsizroq — moliya paneli uchun
                    # 2 soatdan eski ma'lumot qabul qilinmaydi.
                elif cached is not None:
                    # Eski formatdagi yozuv (vaqt belgisi yo'q) — bir marta
                    # qaytarib, fonda yangi formatga ko'chiramiz.
                    _enqueue_refresh(method_path, call_args)
                    return cached

            # Reached only on a miss: ensure the recompute starts from clean inner caches.
            reset_inner_caches()
            result = fn(*args, **kwargs)
            cache.set_value(
                key,
                {"__v": result, "__t": _now()},
                expires_in_sec=DASHBOARD_CACHE_HARD_TTL,
            )
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
    submission of the underlying document.

    Bir so'rov ichida BIR MARTA (2026-10-29): bitta submit bir nechta hook
    uchirishi mumkin (masalan hujjat o'zi + unga bog'liq hujjat, yoki
    `submit` ichidagi `on_update_after_submit`), har biri esa Redis'da
    SCAN+DELETE qiladi. Dashboard keshi bir so'rovda ikki marta
    tozalanishidan hech narsa yutilmaydi.
    """
    if getattr(frappe.local, "dashboard_cache_cleared", False):
        return
    try:
        # O'CHIRMAYMIZ, «eskirgan» deb belgilaymiz (2026-10-29): o'chirish
        # keyingi ochuvchini to'liq hisobni kutishga majbur qilardi. Endi u
        # eski raqamni darhol ko'radi, yangisi fonda hisoblanadi.
        bump_stale_epoch()
        bump_period_stale(getattr(doc, "posting_date", None) if doc else None)
        reset_inner_caches()
        frappe.local.dashboard_cache_cleared = True
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
