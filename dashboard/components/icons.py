"""Small Material Symbols helpers for dashboard presentation components."""

from __future__ import annotations

from html import escape


CATEGORY_ICONS = {
    "Makan": "restaurant",
    "Transport": "directions_car",
    "Belanja": "shopping_bag",
    "Hiburan": "local_activity",
    "Kesehatan": "health_and_safety",
    "Tempat Tinggal": "home",
    "Tagihan & Langganan": "receipt_long",
    "Pendidikan": "school",
    "Lainnya": "account_balance_wallet",
    "Uang Saku": "account_balance_wallet",
    "Gaji": "payments",
    "Freelance": "business_center",
    "Reimbursement": "currency_exchange",
    "Investasi": "trending_up",
}


def material_icon(name: str, *, css_class: str = "") -> str:
    """Return a safe Material Symbols HTML fragment for presentation-only use."""

    classes = "material-symbols-rounded"
    if css_class:
        classes = f"{classes} {css_class}"
    return f'<span class="{escape(classes)}">{escape(name)}</span>'


def category_icon(category: object) -> str:
    """Return the standard icon for a known category or a safe fallback."""

    return material_icon(CATEGORY_ICONS.get(str(category), "category"))
