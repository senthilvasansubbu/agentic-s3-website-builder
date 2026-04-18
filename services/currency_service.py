"""
Currency service — detects visitor location from IP and returns the
appropriate currency code + symbol.
Uses ip-api.com (free, no key required for non-commercial use).
"""
import os
import requests
from typing import Tuple

# Country → (ISO 4217 code, symbol)
COUNTRY_CURRENCY: dict = {
    "US": ("USD", "$"), "GB": ("GBP", "£"), "EU": ("EUR", "€"),
    "DE": ("EUR", "€"), "FR": ("EUR", "€"), "IT": ("EUR", "€"),
    "ES": ("EUR", "€"), "NL": ("EUR", "€"), "BE": ("EUR", "€"),
    "AT": ("EUR", "€"), "IE": ("EUR", "€"), "FI": ("EUR", "€"),
    "PT": ("EUR", "€"), "GR": ("EUR", "€"), "IN": ("INR", "₹"),
    "JP": ("JPY", "¥"), "CN": ("CNY", "¥"), "KR": ("KRW", "₩"),
    "AU": ("AUD", "A$"), "CA": ("CAD", "CA$"), "CH": ("CHF", "CHF"),
    "SE": ("SEK", "kr"), "NO": ("NOK", "kr"), "DK": ("DKK", "kr"),
    "SG": ("SGD", "S$"), "HK": ("HKD", "HK$"), "NZ": ("NZD", "NZ$"),
    "BR": ("BRL", "R$"), "MX": ("MXN", "MX$"), "ZA": ("ZAR", "R"),
    "AE": ("AED", "د.إ"), "SA": ("SAR", "﷼"), "TR": ("TRY", "₺"),
    "RU": ("RUB", "₽"), "PL": ("PLN", "zł"), "CZ": ("CZK", "Kč"),
    "MY": ("MYR", "RM"), "ID": ("IDR", "Rp"), "TH": ("THB", "฿"),
    "PH": ("PHP", "₱"), "VN": ("VND", "₫"), "PK": ("PKR", "₨"),
    "BD": ("BDT", "৳"), "EG": ("EGP", "£"), "NG": ("NGN", "₦"),
    "KE": ("KES", "Ksh"), "GH": ("GHS", "₵"), "AR": ("ARS", "$"),
    "CL": ("CLP", "$"), "CO": ("COP", "$"),
}
DEFAULT_CURRENCY = ("USD", "$")


def currency_from_ip(ip: str) -> Tuple[str, str]:
    """
    Return (currency_code, symbol) for the given IP address.
    Falls back to USD on any error.
    """
    if not ip or ip in ("127.0.0.1", "::1", "testclient"):
        return DEFAULT_CURRENCY
    try:
        resp = requests.get(
            f"http://ip-api.com/json/{ip}?fields=countryCode",
            timeout=4,
        )
        data = resp.json()
        code = data.get("countryCode", "US")
        return COUNTRY_CURRENCY.get(code, DEFAULT_CURRENCY)
    except Exception:
        return DEFAULT_CURRENCY


def format_price(amount: float, currency_code: str, symbol: str) -> str:
    """Format a price for display, e.g. '$12.99' or '€12.99'."""
    return f"{symbol}{amount:,.2f}"
