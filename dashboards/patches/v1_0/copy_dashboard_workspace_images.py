from __future__ import annotations

from pathlib import Path
import shutil

import frappe


SOURCE_DIR = Path("/home/sherzod/Pictures/Dashboards")
TARGET_DIR = Path(frappe.get_app_path("dashboards", "public", "images", "dashboards"))

IMAGE_MAP = {
    "DASHBOARD.jpg": "main-dashboard.jpg",
    "Анализ по месяц.jpg": "monthly-analysis.jpg",
    "ГЛАВНЫЙ.jpg": "overview-dashboard.jpg",
    "Дивидент.jpg": "dividend-analysis.jpg",
    "Ежедневно.jpg": "daily-dashboard.jpg",
    "Касса.jpg": "cash-dashboard.jpg",
    "Клиент.jpg": "customer-dashboard.jpg",
    "Поставшик.jpg": "supplier-dashboard.jpg",
    "Продажа.jpg": "sales-dashboard.jpg",
    "Срав. по кг.jpg": "comparison-by-weight.jpg",
    "Срав. по сумма.jpg": "comparison-by-amount.jpg",
    "Срав. по товар.jpg": "comparison-by-product.jpg",
    "Срав.клиент.jpg": "customer-comparison.jpg",
    "Срав.продукт по клиент.jpg": "product-by-customer.jpg",
    "Срав.продукт.jpg": "product-comparison.jpg",
}


def execute():
    TARGET_DIR.mkdir(parents=True, exist_ok=True)

    for source_name, target_name in IMAGE_MAP.items():
        source_path = SOURCE_DIR / source_name
        target_path = TARGET_DIR / target_name

        if not source_path.exists():
            frappe.log_error(
                title="Dashboard workspace image missing",
                message=f"Expected source image not found: {source_path}",
            )
            continue

        shutil.copy2(source_path, target_path)
