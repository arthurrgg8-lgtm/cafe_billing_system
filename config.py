"""
config.py — CafeBoss runtime configuration
Auto-created and auto-migrated on every startup via migrate().

__getattr__ precedence:
  1. _data (merged JSON + DEFAULTS — always complete)
  2. DEFAULTS (belt-and-suspenders fallback)
  3. AttributeError (truly unknown name)
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

SETTINGS_FILE = Path("cafe_settings.json")

DEFAULTS: dict[str, Any] = {
    # Identity
    "cafe_name":                  "CafeBoss",
    "cafe_tagline":               "Modern Billing System",

    # Tokens
    "token_count":                10,
    "token_label_prefix":         "Token",
    "token_types_enabled":        ["dine_in", "takeaway", "delivery", "online"],
    "token_max":                  50,        # hard cap — owner cannot exceed this

    # Currency & Tax
    "currency_symbol":            "₹",
    "default_tax_rate":           0.0,
    "show_tax_on_receipt":        False,

    # Security
    "min_password_length":        8,
    "password_expiry_days":       30,
    "owner_session_timeout_mins": 60,
    "dev_session_timeout_mins":   30,

    # Bill saving
    "bills_folder":               "bills",
    "audit_folder":               "audit_logs",
    "save_csv_receipt":           True,

    # UI behaviour
    "tokens_per_row":             5,
    "confirm_before_payment":     True,

    # Payment methods
    "payment_methods":            ["cash", "card", "upi", "online"],

    # Working date
    "work_date_lookback_days":    3,         # max days back cashier can set working date
}

_ALLOWED_TOKEN_TYPES = {"dine_in", "takeaway", "delivery", "online"}
_ALLOWED_PAYMENT_METHODS = {"cash", "card", "upi", "online"}


# ── Load / Save / Migrate ─────────────────────────────────────────────────────

def _atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f"{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _to_int(value: Any, default: int, min_value: int, max_value: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(min_value, min(max_value, parsed))


def _to_float(value: Any, default: float, min_value: float, max_value: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = default
    return max(min_value, min(max_value, parsed))


def _normalize(raw: dict[str, Any]) -> dict[str, Any]:
    out = dict(DEFAULTS)

    out["cafe_name"] = str(raw.get("cafe_name", out["cafe_name"])).strip() or DEFAULTS["cafe_name"]
    out["cafe_tagline"] = str(raw.get("cafe_tagline", out["cafe_tagline"])).strip()
    out["currency_symbol"] = str(raw.get("currency_symbol", out["currency_symbol"])).strip()[:4] or DEFAULTS["currency_symbol"]
    out["bills_folder"] = str(raw.get("bills_folder", out["bills_folder"])).strip() or DEFAULTS["bills_folder"]
    out["audit_folder"] = str(raw.get("audit_folder", out["audit_folder"])).strip() or DEFAULTS["audit_folder"]
    out["token_label_prefix"] = str(raw.get("token_label_prefix", out["token_label_prefix"])).strip() or DEFAULTS["token_label_prefix"]

    out["token_count"] = _to_int(raw.get("token_count", out["token_count"]), DEFAULTS["token_count"], 1, 500)
    out["token_max"] = _to_int(raw.get("token_max", out["token_max"]), DEFAULTS["token_max"], 1, 500)
    out["min_password_length"] = _to_int(raw.get("min_password_length", out["min_password_length"]), DEFAULTS["min_password_length"], 8, 128)
    out["password_expiry_days"] = _to_int(raw.get("password_expiry_days", out["password_expiry_days"]), DEFAULTS["password_expiry_days"], 0, 3650)
    out["owner_session_timeout_mins"] = _to_int(raw.get("owner_session_timeout_mins", out["owner_session_timeout_mins"]), DEFAULTS["owner_session_timeout_mins"], 0, 1440)
    out["dev_session_timeout_mins"] = _to_int(raw.get("dev_session_timeout_mins", out["dev_session_timeout_mins"]), DEFAULTS["dev_session_timeout_mins"], 0, 1440)
    out["tokens_per_row"] = _to_int(raw.get("tokens_per_row", out["tokens_per_row"]), DEFAULTS["tokens_per_row"], 1, 8)
    out["work_date_lookback_days"] = _to_int(raw.get("work_date_lookback_days", out["work_date_lookback_days"]), DEFAULTS["work_date_lookback_days"], 1, 30)
    out["default_tax_rate"] = _to_float(raw.get("default_tax_rate", out["default_tax_rate"]), DEFAULTS["default_tax_rate"], 0.0, 100.0)

    out["show_tax_on_receipt"] = bool(raw.get("show_tax_on_receipt", out["show_tax_on_receipt"]))
    out["save_csv_receipt"] = bool(raw.get("save_csv_receipt", out["save_csv_receipt"]))
    out["confirm_before_payment"] = bool(raw.get("confirm_before_payment", out["confirm_before_payment"]))

    token_types = raw.get("token_types_enabled", out["token_types_enabled"])
    if not isinstance(token_types, list):
        token_types = list(DEFAULTS["token_types_enabled"])
    token_types = [str(t).strip() for t in token_types if str(t).strip() in _ALLOWED_TOKEN_TYPES]
    out["token_types_enabled"] = token_types or list(DEFAULTS["token_types_enabled"])

    pay_methods = raw.get("payment_methods", out["payment_methods"])
    if not isinstance(pay_methods, list):
        pay_methods = list(DEFAULTS["payment_methods"])
    pay_methods = [str(m).strip() for m in pay_methods if str(m).strip() in _ALLOWED_PAYMENT_METHODS]
    out["payment_methods"] = pay_methods or list(DEFAULTS["payment_methods"])

    if out["token_count"] > out["token_max"]:
        out["token_count"] = out["token_max"]

    return out

def _load_raw() -> dict[str, Any]:
    if not SETTINGS_FILE.exists():
        return {}
    try:
        return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def load() -> dict[str, Any]:
    return _normalize(_load_raw())


def save(updates: dict[str, Any]) -> None:
    current = _load_raw()
    for k, v in updates.items():
        if k in DEFAULTS:
            current[k] = v
    _atomic_write_json(SETTINGS_FILE, _normalize(current))


def migrate() -> None:
    """Write any missing DEFAULTS keys into existing JSON. Safe every startup."""
    raw = _load_raw()
    normalized = _normalize(raw)
    if raw != normalized:
        _atomic_write_json(SETTINGS_FILE, normalized)


def ensure_file_exists() -> None:
    migrate()


# ── Typed Settings wrapper ────────────────────────────────────────────────────

class Settings:
    def __init__(self) -> None:
        self._data: dict[str, Any] = load()

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            raise AttributeError(name)
        data = object.__getattribute__(self, "_data")
        if name in data:
            return data[name]
        if name in DEFAULTS:
            return DEFAULTS[name]
        raise AttributeError(f"Unknown setting: '{name}'. Add to DEFAULTS first.")

    @property
    def cafe_name(self) -> str:               return str(self._data["cafe_name"])
    @property
    def cafe_tagline(self) -> str:            return str(self._data["cafe_tagline"])
    @property
    def token_count(self) -> int:             return int(self._data["token_count"])
    @property
    def token_label_prefix(self) -> str:      return str(self._data["token_label_prefix"])
    @property
    def token_types_enabled(self) -> list:    return list(self._data["token_types_enabled"])
    @property
    def token_max(self) -> int:               return int(self._data["token_max"])
    @property
    def currency_symbol(self) -> str:         return str(self._data["currency_symbol"])
    @property
    def default_tax_rate(self) -> float:      return float(self._data["default_tax_rate"])
    @property
    def show_tax_on_receipt(self) -> bool:    return bool(self._data["show_tax_on_receipt"])
    @property
    def min_password_length(self) -> int:     return int(self._data["min_password_length"])
    @property
    def password_expiry_days(self) -> int:    return int(self._data["password_expiry_days"])
    @property
    def owner_session_timeout_mins(self) -> int: return int(self._data["owner_session_timeout_mins"])
    @property
    def dev_session_timeout_mins(self) -> int:   return int(self._data["dev_session_timeout_mins"])
    @property
    def bills_folder(self) -> Path:           return Path(str(self._data["bills_folder"]))
    @property
    def audit_folder(self) -> Path:           return Path(str(self._data["audit_folder"]))
    @property
    def save_csv_receipt(self) -> bool:       return bool(self._data["save_csv_receipt"])
    @property
    def tokens_per_row(self) -> int:          return int(self._data["tokens_per_row"])
    @property
    def confirm_before_payment(self) -> bool: return bool(self._data["confirm_before_payment"])
    @property
    def payment_methods(self) -> list:        return list(self._data["payment_methods"])
    @property
    def work_date_lookback_days(self) -> int: return int(self._data["work_date_lookback_days"])
