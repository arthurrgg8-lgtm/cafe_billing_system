"""
CafeBoss - Modern Billing System
Refactored for production quality: type safety, atomic I/O, proper error handling,
constant-time auth, and clean separation of concerns.
"""

from __future__ import annotations

import csv
import hashlib
import hmac
import os
import platform
import secrets
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

import ui

# ======================================================
# CONFIGURATION
# ======================================================

@dataclass(frozen=True)
class Config:
    """Central configuration — change behaviour here, not scattered across the file."""
    default_tokens: int = 10
    min_password_length: int = 8
    password_expiry_days: int = 30

    menu_file: Path = Path("menu_items.csv")
    audit_folder: Path = Path("audit_logs")
    bills_folder: Path = Path("bills")
    password_file: Path = Path("owner_password.hash")
    password_expiry_file: Path = Path("password_expiry.txt")


CFG = Config()

# ======================================================
# PAGE CONFIG
# ======================================================

st.set_page_config(
    page_title="CafeBoss - Modern Billing System",
    page_icon="☕",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ======================================================
# BOOTSTRAP: create required directories & files
# ======================================================

CFG.audit_folder.mkdir(parents=True, exist_ok=True)
CFG.bills_folder.mkdir(parents=True, exist_ok=True)

if not CFG.menu_file.exists():
    pd.DataFrame(columns=["Item", "Price", "Category"]).to_csv(CFG.menu_file, index=False)

# ======================================================
# SESSION STATE
# ======================================================

def init_session_state() -> None:
    """Initialise all session-state keys in one place."""
    defaults: dict[str, Any] = {
        "authenticated_owner": False,
        "token_status": {i: False for i in range(1, CFG.default_tokens + 1)},
        "token_items": {i: [] for i in range(1, CFG.default_tokens + 1)},
        "selected_token": 1,
        "show_owner_login": False,
        "confirm_payment": False,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


init_session_state()

# ======================================================
# SECURITY
# ======================================================

class PasswordManager:
    """Handles password hashing, verification, persistence, and expiry."""

    @staticmethod
    def hash(password: str, salt: str | None = None) -> str:
        if salt is None:
            salt = secrets.token_hex(16)
        digest = hashlib.sha256((salt + password).encode()).hexdigest()
        return f"{salt}${digest}"

    @classmethod
    def verify(cls, password: str, stored_value: str) -> bool:
        """Constant-time comparison to prevent timing attacks."""
        try:
            salt, _ = stored_value.split("$", 1)
            expected = cls.hash(password, salt)
            return hmac.compare_digest(expected.encode(), stored_value.encode())
        except (ValueError, AttributeError):
            return False

    @classmethod
    def save(cls, password: str) -> None:
        if len(password) < CFG.min_password_length:
            raise ValueError(
                f"Password must be at least {CFG.min_password_length} characters."
            )
        hashed = cls.hash(password)
        CFG.password_file.write_text(hashed)
        expiry = datetime.now() + timedelta(days=CFG.password_expiry_days)
        CFG.password_expiry_file.write_text(expiry.strftime("%Y-%m-%d"))

    @staticmethod
    def exists() -> bool:
        return CFG.password_file.exists()

    @staticmethod
    def is_expired() -> bool:
        if not CFG.password_expiry_file.exists():
            return False
        try:
            expiry = datetime.strptime(
                CFG.password_expiry_file.read_text().strip(), "%Y-%m-%d"
            )
            return datetime.now() > expiry
        except ValueError:
            return False

    @staticmethod
    def load() -> str:
        return CFG.password_file.read_text().strip()


# ======================================================
# FILESYSTEM HELPERS
# ======================================================

def get_save_location() -> tuple[Path, str]:
    """Return (path, human-readable label) for bill storage."""
    if platform.system() == "Windows":
        downloads = Path.home() / "Downloads"
        if downloads.exists():
            return downloads, "Downloads"
    return CFG.bills_folder.resolve(), "Bills Folder"


def _atomic_write_csv(filepath: Path, rows: list[list[Any]], header: list[str]) -> None:
    """Write CSV atomically: write to a temp file then rename to avoid partial writes."""
    parent = filepath.parent
    parent.mkdir(parents=True, exist_ok=True)

    fd, tmp_path = tempfile.mkstemp(dir=parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(rows)
        os.replace(tmp_path, filepath)  # atomic on POSIX; best-effort on Windows
    except Exception:
        os.unlink(tmp_path)
        raise


# ======================================================
# BILLING SERVICE
# ======================================================

class BillingService:
    """All billing I/O in one place."""

    @staticmethod
    def save_bill(
        token: int,
        items: list[dict[str, Any]],
        total: float,
    ) -> tuple[Path, str, str]:
        if not items or total <= 0:
            raise ValueError("Cannot save an empty or zero-value bill.")

        save_path, location_desc = get_save_location()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"token{token}_{timestamp}.csv"

        header = ["Token", "Item", "Quantity", "Unit Price", "Subtotal"]
        rows: list[list[Any]] = [
            [token, item["Item"], item["Quantity"], item["Price"], item["Subtotal"]]
            for item in items
        ]
        rows.append(["", "", "", "TOTAL", total])
        rows.append(["", "", "", "PAID AT", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])

        primary_path = save_path / filename
        _atomic_write_csv(primary_path, rows, header)

        # Backup (bills folder); skip silently if primary IS the bills folder
        backup_path = CFG.bills_folder / filename
        if backup_path != primary_path:
            _atomic_write_csv(backup_path, rows[:-1], header)  # omit PAID AT in backup

        return primary_path, filename, location_desc

    @staticmethod
    def save_audit_entry(
        token: int,
        items: list[dict[str, Any]],
        total: float,
        filename: str,
    ) -> None:
        today = datetime.now().strftime("%Y-%m-%d")
        audit_file = CFG.audit_folder / f"audit_{today}.csv"
        write_header = not audit_file.exists()

        with audit_file.open("a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if write_header:
                writer.writerow(["Timestamp", "Token", "Total", "Filename", "Item_Count"])
            writer.writerow([
                datetime.now().strftime("%H:%M:%S"),
                token,
                total,
                filename,
                len(items),
            ])

    @staticmethod
    def reset_token(token: int) -> None:
        st.session_state.token_items[token].clear()
        st.session_state.token_status[token] = False


# ======================================================
# OWNER DASHBOARD SERVICE
# ======================================================

class DashboardService:
    @staticmethod
    def get_today_stats() -> tuple[int, float, list[dict[str, Any]]]:
        today = datetime.now().strftime("%Y-%m-%d")
        audit_file = CFG.audit_folder / f"audit_{today}.csv"

        if not audit_file.exists():
            return 0, 0.0, []

        df = pd.read_csv(audit_file)
        return len(df), float(df["Total"].sum()), df.to_dict("records")

    @staticmethod
    def verify_transactions() -> list[dict[str, Any]]:
        today = datetime.now().strftime("%Y-%m-%d")
        audit_file = CFG.audit_folder / f"audit_{today}.csv"
        save_path, _ = get_save_location()
        missing: list[dict[str, Any]] = []

        if not audit_file.exists():
            return missing

        df = pd.read_csv(audit_file)
        for _, row in df.iterrows():
            fname = row["Filename"]
            if not (
                (save_path / fname).exists()
                or (CFG.bills_folder / fname).exists()
            ):
                missing.append(row.to_dict())

        return missing


# ======================================================
# MENU SERVICE
# ======================================================

class MenuService:
    @staticmethod
    def load() -> pd.DataFrame:
        return pd.read_csv(CFG.menu_file)

    @staticmethod
    def save(df: pd.DataFrame) -> None:
        df.to_csv(CFG.menu_file, index=False)

    @classmethod
    def add_item(cls, name: str, price: float, category: str) -> None:
        if not name.strip() or price <= 0:
            raise ValueError("Item name must be non-empty and price must be positive.")
        df = cls.load()
        new_row = pd.DataFrame({"Item": [name], "Price": [price], "Category": [category]})
        cls.save(pd.concat([df, new_row], ignore_index=True))

    @classmethod
    def update_price(cls, idx: int, new_price: float) -> None:
        df = cls.load()
        if not (0 <= idx < len(df)):
            raise IndexError(f"Menu index {idx} out of range.")
        df.at[idx, "Price"] = new_price
        cls.save(df)

    @classmethod
    def delete_item(cls, idx: int) -> None:
        df = cls.load()
        if not (0 <= idx < len(df)):
            raise IndexError(f"Menu index {idx} out of range.")
        cls.save(df.drop(idx).reset_index(drop=True))


# ======================================================
# NAVIGATION HELPERS (replaces lambda hacks)
# ======================================================

def select_token(token: int) -> None:
    st.session_state.selected_token = token
    st.rerun()


def logout_owner() -> None:
    st.session_state.authenticated_owner = False
    st.rerun()


# ======================================================
# PASSWORD SETUP (first-run)
# ======================================================

if not PasswordManager.exists():
    ui.load_fancy_css()
    ui.password_setup_ui(PasswordManager.save)
    st.stop()

# ======================================================
# MAIN UI
# ======================================================

ui.load_fancy_css()
ui.fancy_header()

with st.sidebar:
    ui.token_board(
        selected_token=st.session_state.selected_token,
        token_status=st.session_state.token_status,
        on_token_click=select_token,
    )

    save_path, loc = get_save_location()
    ui.save_location_info(str(save_path), loc)

    if st.button("👑 OWNER DASHBOARD", use_container_width=True):
        st.session_state.show_owner_login = True
        st.rerun()

# ======================================================
# OWNER AUTHENTICATION
# ======================================================

if st.session_state.show_owner_login and not st.session_state.authenticated_owner:
    if PasswordManager.is_expired():
        st.warning("Owner password has expired. Please set a new password.")
        ui.password_setup_ui(PasswordManager.save)
        st.stop()

    password = ui.owner_login_ui()
    if password:
        if PasswordManager.verify(password, PasswordManager.load()):
            st.session_state.authenticated_owner = True
            st.session_state.show_owner_login = False
            st.rerun()
        else:
            st.error("Invalid password.")

# ======================================================
# OWNER DASHBOARD
# ======================================================

if st.session_state.authenticated_owner:
    total_bills, total_revenue, recent_bills = DashboardService.get_today_stats()
    missing_files = DashboardService.verify_transactions()

    ui.owner_dashboard_ui(
        total_bills,
        total_revenue,
        recent_bills,
        missing_files,
        on_logout=logout_owner,
        on_download_report=lambda: None,  # placeholder — implement export when ready
    )
    st.stop()

# ======================================================
# CASHIER INTERFACE
# ======================================================

selected_token: int = st.session_state.selected_token
menu_df = MenuService.load()

tab1, tab2 = st.tabs(["🧾 Billing", "📋 Menu"])

with tab1:
    col1, col2 = st.columns([2, 1])

    with col1:
        def handle_delete(idx: int) -> None:
            try:
                st.session_state.token_items[selected_token].pop(idx)
                if not st.session_state.token_items[selected_token]:
                    st.session_state.token_status[selected_token] = False
                st.rerun()
            except IndexError:
                st.error("Item no longer exists — please refresh.")

        def handle_payment(items: list[dict[str, Any]], total: float) -> None:
            try:
                _, name, _ = BillingService.save_bill(selected_token, items, total)
                BillingService.save_audit_entry(selected_token, items, total, name)
                BillingService.reset_token(selected_token)
                st.success("Payment successful.")
                st.rerun()
            except (ValueError, OSError, RuntimeError) as exc:
                st.error(str(exc))

        def set_confirm(val: bool) -> None:
            st.session_state.confirm_payment = val

        ui.bill_view(
            selected_token,
            st.session_state.token_items[selected_token],
            handle_delete,
            handle_payment,
            st.session_state.confirm_payment,
            set_confirm,
        )

    with col2:
        def handle_add_to_bill(name: str, price: float, qty: int) -> None:
            if qty <= 0:
                st.error("Quantity must be a positive number.")
                return
            st.session_state.token_items[selected_token].append({
                "Item": name,
                "Price": price,
                "Quantity": qty,
                "Subtotal": price * qty,
            })
            st.session_state.token_status[selected_token] = True
            st.rerun()

        ui.item_selector(menu_df, selected_token, handle_add_to_bill)

with tab2:
    ui.menu_view(
        menu_df,
        MenuService.add_item,
        MenuService.update_price,
        MenuService.delete_item,
    )

ui.fancy_footer()
