"""
config.py — CafeBoss runtime configuration
Loads from cafe_settings.json. Auto-created and auto-migrated on every startup.

Key fixes vs previous version:
  - __getattr__ now checks _data first, falls back to DEFAULTS, THEN raises.
    This means any key in DEFAULTS is always accessible even if the JSON
    on disk was written before that key was added (forward-compatible reads).
  - migrate() is called on every startup: it writes any missing DEFAULTS keys
    into the existing JSON so the file stays in sync with the codebase.
  - ensure_file_exists() now calls migrate() rather than only writing on first run.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SETTINGS_FILE = Path("cafe_settings.json")

# ──────────────────────────────────────────────────────────────────────────────
# DEFAULTS — single source of truth for all settings
# Adding a key here is enough; migrate() will push it into any existing JSON.
# ──────────────────────────────────────────────────────────────────────────────

DEFAULTS: dict[str, Any] = {
    # ── Identity ──────────────────────────────────────────────────────────────
    "cafe_name":                  "CafeBoss",
    "cafe_tagline":               "Modern Billing System",

    # ── Tokens ────────────────────────────────────────────────────────────────
    "token_count":                10,
    "token_label_prefix":         "Token",
    "token_types_enabled":        ["dine_in", "takeaway", "delivery", "online"],

    # ── Currency & Tax ────────────────────────────────────────────────────────
    "currency_symbol":            "₹",
    "default_tax_rate":           0.0,
    "show_tax_on_receipt":        False,

    # ── Security ──────────────────────────────────────────────────────────────
    "min_password_length":        8,
    "password_expiry_days":       30,
    "owner_session_timeout_mins": 60,    # 0 = never expire
    "dev_session_timeout_mins":   30,    # dev sessions expire faster

    # ── Bill saving ───────────────────────────────────────────────────────────
    "bills_folder":               "bills",
    "audit_folder":               "audit_logs",
    "save_csv_receipt":           True,

    # ── UI behaviour ──────────────────────────────────────────────────────────
    "tokens_per_row":             5,
    "confirm_before_payment":     True,

    # ── Payment methods ───────────────────────────────────────────────────────
    "payment_methods":            ["cash", "card", "upi", "online"],
}


# ──────────────────────────────────────────────────────────────────────────────
# LOAD / SAVE / MIGRATE
# ──────────────────────────────────────────────────────────────────────────────

def _load_raw() -> dict[str, Any]:
    if not SETTINGS_FILE.exists():
        return {}
    try:
        return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def load() -> dict[str, Any]:
    """
    Return merged settings: DEFAULTS overlaid with whatever is in JSON.
    Unknown keys in JSON are silently ignored.
    Missing keys in JSON are filled from DEFAULTS.
    This is always safe regardless of how old the JSON file is.
    """
    raw = _load_raw()
    return {k: raw.get(k, v) for k, v in DEFAULTS.items()}


def save(updates: dict[str, Any]) -> None:
    """
    Persist a partial or full settings dict.
    Only keys present in DEFAULTS are written.
    """
    current = _load_raw()
    for k, v in updates.items():
        if k in DEFAULTS:
            current[k] = v
    SETTINGS_FILE.write_text(
        json.dumps(current, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def migrate() -> None:
    """
    Write any DEFAULTS keys that are missing from the on-disk JSON.
    Safe to call on every startup — only writes when something is missing.
    Also creates the file from scratch on first run.
    """
    raw = _load_raw()
    missing = {k: v for k, v in DEFAULTS.items() if k not in raw}
    if missing:
        raw.update(missing)
        SETTINGS_FILE.write_text(
            json.dumps(raw, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )


def ensure_file_exists() -> None:
    """Call once at startup. Creates or migrates the settings file."""
    migrate()


# ──────────────────────────────────────────────────────────────────────────────
# TYPED SETTINGS WRAPPER
# ──────────────────────────────────────────────────────────────────────────────

class Settings:
    """
    Attribute-style access to merged settings with type guarantees.
    Instantiate once per Streamlit render cycle (load() is cheap).

    __getattr__ precedence:
      1. Check self._data (merged result — always has every DEFAULTS key)
      2. Fall back to DEFAULTS (belt-and-suspenders)
      3. Raise AttributeError only for truly unknown names
    """

    def __init__(self) -> None:
        self._data: dict[str, Any] = load()

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            raise AttributeError(name)
        # _data is populated in __init__ via load() which always merges DEFAULTS
        # so every DEFAULTS key is guaranteed to be present.
        data = object.__getattribute__(self, "_data")
        if name in data:
            return data[name]
        if name in DEFAULTS:
            return DEFAULTS[name]
        raise AttributeError(
            f"Unknown setting: '{name}'. "
            f"Add it to DEFAULTS in config.py first."
        )

    # ── Typed properties (explicit types prevent silent coercion bugs) ─────────

    @property
    def cafe_name(self) -> str:
        return str(self._data["cafe_name"])

    @property
    def cafe_tagline(self) -> str:
        return str(self._data["cafe_tagline"])

    @property
    def token_count(self) -> int:
        return int(self._data["token_count"])

    @property
    def token_label_prefix(self) -> str:
        return str(self._data["token_label_prefix"])

    @property
    def token_types_enabled(self) -> list[str]:
        return list(self._data["token_types_enabled"])

    @property
    def currency_symbol(self) -> str:
        return str(self._data["currency_symbol"])

    @property
    def default_tax_rate(self) -> float:
        return float(self._data["default_tax_rate"])

    @property
    def show_tax_on_receipt(self) -> bool:
        return bool(self._data["show_tax_on_receipt"])

    @property
    def min_password_length(self) -> int:
        return int(self._data["min_password_length"])

    @property
    def password_expiry_days(self) -> int:
        return int(self._data["password_expiry_days"])

    @property
    def owner_session_timeout_mins(self) -> int:
        return int(self._data["owner_session_timeout_mins"])

    @property
    def dev_session_timeout_mins(self) -> int:
        return int(self._data["dev_session_timeout_mins"])

    @property
    def bills_folder(self) -> Path:
        return Path(str(self._data["bills_folder"]))

    @property
    def audit_folder(self) -> Path:
        return Path(str(self._data["audit_folder"]))

    @property
    def save_csv_receipt(self) -> bool:
        return bool(self._data["save_csv_receipt"])

    @property
    def tokens_per_row(self) -> int:
        return int(self._data["tokens_per_row"])

    @property
    def confirm_before_payment(self) -> bool:
        return bool(self._data["confirm_before_payment"])

    @property
    def payment_methods(self) -> list[str]:
        return list(self._data["payment_methods"])