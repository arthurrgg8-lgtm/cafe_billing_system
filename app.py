"""
CafeBoss — app.py

Architecture note — why _render() exists:
  Streamlit re-executes app.py top-to-bottom on every browser interaction.
  All ui.* calls must happen AFTER all imports are fully resolved.
  Placing them inside _render() (called at the very bottom) guarantees:
    1. `ui` module is 100% initialized before any attribute is accessed
    2. No circular-import AttributeErrors regardless of Python import order
    3. Bootstrap code (db, config, session state) still runs at module level
       as Streamlit requires for set_page_config and session_state.setdefault
"""

from __future__ import annotations

import csv
import hashlib
import hmac
import os
import platform
import secrets
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import streamlit as st

import config as cfg_module
import db
import ui  # imported here — _render() accesses it only after full initialization

# ──────────────────────────────────────────────────────────────────────────────
# BOOTSTRAP  (runs at module level — required by Streamlit)
# ──────────────────────────────────────────────────────────────────────────────

cfg_module.ensure_file_exists()
CFG = cfg_module.Settings()

db.init_db()
db.TokenService.bootstrap_tokens(
    CFG.token_count, CFG.token_label_prefix, CFG.token_max
)

_menu_csv = Path("menu_items.csv")
if _menu_csv.exists():
    db.MenuDB.import_from_csv(_menu_csv)

CFG.bills_folder.mkdir(parents=True, exist_ok=True)
CFG.audit_folder.mkdir(parents=True, exist_ok=True)

# ──────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG  (must be first Streamlit call — module level)
# ──────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title=f"{CFG.cafe_name} · {CFG.cafe_tagline}",
    page_icon="☕",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────────────────────────────────────────
# CREDENTIAL STORE
# ──────────────────────────────────────────────────────────────────────────────

class CredentialStore:

    def __init__(self, role: str) -> None:
        self.role         = role
        self._hash_file   = Path(f"{role}_password.hash")
        self._expiry_file = Path(f"{role}_password_expiry.txt")

    @staticmethod
    def _hash(password: str, salt: str | None = None) -> str:
        if salt is None:
            salt = secrets.token_hex(16)
        digest = hashlib.sha256((salt + password).encode()).hexdigest()
        return f"{salt}${digest}"

    def exists(self) -> bool:
        return self._hash_file.exists()

    def save(self, password: str) -> None:
        cfg     = cfg_module.Settings()
        min_len = cfg.min_password_length
        if len(password) < min_len:
            raise ValueError(f"Password must be at least {min_len} characters.")
        self._hash_file.write_text(self._hash(password))
        expiry_days = cfg.password_expiry_days
        if expiry_days > 0:
            expiry = datetime.now() + timedelta(days=expiry_days)
            self._expiry_file.write_text(expiry.strftime("%Y-%m-%d"))

    def verify(self, password: str) -> bool:
        if not self.exists():
            return False
        stored = self._hash_file.read_text().strip()
        try:
            salt, _ = stored.split("$", 1)
            expected = self._hash(password, salt)
            return hmac.compare_digest(expected.encode(), stored.encode())
        except (ValueError, AttributeError):
            return False

    def is_expired(self) -> bool:
        if not self._expiry_file.exists():
            return False
        try:
            expiry = datetime.strptime(
                self._expiry_file.read_text().strip(), "%Y-%m-%d"
            )
            return datetime.now() > expiry
        except ValueError:
            return False


_owner_creds = CredentialStore("owner")
_dev_creds   = CredentialStore("dev")

# ──────────────────────────────────────────────────────────────────────────────
# SESSION STATE  (setdefault calls must be at module level)
# ──────────────────────────────────────────────────────────────────────────────

_TODAY = date.today().isoformat()


def _init_session_state() -> None:
    defaults: dict[str, Any] = {
        "authenticated_owner": False,
        "owner_authed_at":     None,
        "show_owner_login":    False,
        "authenticated_dev":   False,
        "dev_authed_at":       None,
        "selected_token":      None,
        "confirm_payment":     False,
        "last_bill_download":  None,
        "work_date":           _TODAY,
        "show_date_picker":    False,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


_init_session_state()

# ──────────────────────────────────────────────────────────────────────────────
# PURE HELPERS  (no ui.* calls — safe at module level)
# ──────────────────────────────────────────────────────────────────────────────

def _validate_work_date(d: str) -> str | None:
    """Return error string if invalid, None if OK."""
    try:
        candidate = date.fromisoformat(d)
    except ValueError:
        return "Invalid date format."
    today    = date.today()
    if candidate > today:
        return f"Cannot set a future date. Today is {today.isoformat()}."
    earliest = today - timedelta(days=CFG.work_date_lookback_days)
    if candidate < earliest:
        return (
            f"Cannot go back more than {CFG.work_date_lookback_days} day(s). "
            f"Earliest allowed: {earliest.isoformat()}."
        )
    return None


def _session_valid(auth_key: str, authed_at_key: str, timeout_mins: int) -> bool:
    if not st.session_state.get(auth_key, False):
        return False
    if timeout_mins <= 0:
        return True
    authed_at = st.session_state.get(authed_at_key)
    if authed_at is None:
        return False
    return (datetime.now() - authed_at).total_seconds() / 60 < timeout_mins


def _owner_session_valid() -> bool:
    return _session_valid(
        "authenticated_owner", "owner_authed_at",
        CFG.owner_session_timeout_mins,
    )


def _dev_session_valid() -> bool:
    return _session_valid(
        "authenticated_dev", "dev_authed_at",
        CFG.dev_session_timeout_mins,
    )


def _select_token(token_id: int) -> None:
    st.session_state.selected_token = token_id
    st.rerun()


def _logout_owner() -> None:
    st.session_state.authenticated_owner = False
    st.session_state.owner_authed_at     = None
    st.rerun()


def _logout_dev() -> None:
    st.session_state.authenticated_dev = False
    st.session_state.dev_authed_at     = None
    st.rerun()


def _get_save_location() -> tuple[Path, str]:
    if platform.system() == "Windows":
        dl = Path.home() / "Downloads"
        if dl.exists():
            return dl, "Downloads"
    return CFG.bills_folder.resolve(), "Bills Folder"


def _atomic_write_csv(filepath: Path, rows: list[list[Any]],
                      header: list[str]) -> None:
    filepath.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=filepath.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(header)
            w.writerows(rows)
        os.replace(tmp, filepath)
    except Exception:
        os.unlink(tmp)
        raise


def _write_csv_receipt(
    bill_id: str,
    token_label: str,
    items: list[dict[str, Any]],
    total: float,
    payment_method: str,
    work_date: str,
) -> tuple[Path, str, str]:
    save_path, location_desc = _get_save_location()
    filename = f"bill_{work_date}_{bill_id[:8]}.csv"
    header   = ["Token", "Item", "Quantity", "Unit Price", "Subtotal"]
    rows: list[list[Any]] = [
        [token_label, i.get("item_name", ""), i.get("quantity", 1),
         i.get("unit_price", 0), i.get("subtotal", 0)]
        for i in items
    ]
    rows += [
        ["", "", "", "TOTAL",     total],
        ["", "", "", "PAYMENT",   payment_method.upper()],
        ["", "", "", "WORK DATE", work_date],
        ["", "", "", "PAID AT",   datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
    ]
    primary = save_path / filename
    _atomic_write_csv(primary, rows, header)
    backup = CFG.bills_folder / filename
    if backup != primary:
        _atomic_write_csv(backup, rows, header)
    return primary, filename, location_desc


# ──────────────────────────────────────────────────────────────────────────────
# _render()  — every ui.* call lives here
# Called once at the bottom of this file.
# By the time _render() is invoked, all imports are fully resolved.
# ──────────────────────────────────────────────────────────────────────────────

def _render() -> None:  # noqa: C901

    # ── Stale work-date reset ─────────────────────────────────────────────────
    wd = st.session_state.work_date
    if wd < _TODAY and not db.OrderService.has_any_open_orders():
        st.session_state.work_date = _TODAY

    # ── CSS ───────────────────────────────────────────────────────────────────
    ui.load_fancy_css()

    # ── First-run wizard ──────────────────────────────────────────────────────
    if not _owner_creds.exists():
        ui.setup_wizard_ui(
            role="owner",
            title="☕ Welcome to CafeBoss",
            subtitle="Set the Owner password to continue",
            on_save=_owner_creds.save,
        )
        st.stop()

    if not _dev_creds.exists():
        ui.setup_wizard_ui(
            role="dev",
            title="🔧 Developer Setup",
            subtitle="Set the Developer password to protect system settings",
            on_save=_dev_creds.save,
        )
        st.stop()

    # ── Header ────────────────────────────────────────────────────────────────
    ui.fancy_header(CFG.cafe_name, CFG.cafe_tagline)

    all_tokens = db.TokenService.get_all()
    if st.session_state.selected_token is None and all_tokens:
        st.session_state.selected_token = all_tokens[0]["id"]

    # ── Sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:

        def _handle_date_change(new_date_str: str) -> None:
            err = _validate_work_date(new_date_str)
            if err:
                st.session_state["_date_error"] = err
                return
            if db.OrderService.has_any_open_orders():
                n = db.OrderService.get_open_token_count()
                st.session_state["_date_error"] = (
                    f"Cannot change date — {n} token(s) have open orders. "
                    "Pay or clear them first."
                )
                return
            st.session_state.work_date        = new_date_str
            st.session_state.show_date_picker = False
            st.session_state.pop("_date_error", None)
            st.rerun()

        def _handle_date_picker_toggle() -> None:
            st.session_state.show_date_picker = (
                not st.session_state.show_date_picker
            )
            st.rerun()

        ui.working_date_ui(
            work_date=st.session_state.work_date,
            today=_TODAY,
            lookback_days=CFG.work_date_lookback_days,
            show_picker=st.session_state.show_date_picker,
            date_error=st.session_state.pop("_date_error", None),
            on_toggle_picker=_handle_date_picker_toggle,
            on_change_date=_handle_date_change,
        )

        ui.token_board(
            tokens=all_tokens,
            selected_token_id=st.session_state.selected_token,
            tokens_per_row=CFG.tokens_per_row,
            on_token_click=_select_token,
        )

        save_path, loc = _get_save_location()
        ui.save_location_info(str(save_path), loc)

        if st.button("👑 OWNER DASHBOARD", use_container_width=True):
            st.session_state.show_owner_login = True
            st.rerun()

    # ── Owner auth gate ───────────────────────────────────────────────────────
    if st.session_state.show_owner_login and not _owner_session_valid():
        if _owner_creds.is_expired():
            st.warning("Owner password has expired. Please set a new one.")
            ui.setup_wizard_ui(
                role="owner",
                title="🔑 Reset Owner Password",
                subtitle="Password expired — set a new one to continue",
                on_save=_owner_creds.save,
            )
            st.stop()

        result = ui.role_login_ui(role="owner", label="👑 Owner Access")
        if result == "cancel":
            st.session_state.show_owner_login = False
            st.rerun()
        elif result:
            if _owner_creds.verify(result):
                st.session_state.authenticated_owner = True
                st.session_state.owner_authed_at     = datetime.now()
                st.session_state.show_owner_login    = False
                st.rerun()
            else:
                st.error("Invalid owner password.")

    # ── Owner dashboard ───────────────────────────────────────────────────────
    if _owner_session_valid():
        _dash_date_key = "dashboard_view_date"
        st.session_state.setdefault(_dash_date_key, _TODAY)
        dash_date = st.session_state[_dash_date_key]

        total_bills, total_revenue = db.BillService.get_stats_by_date(dash_date)
        recent_bills     = db.BillService.get_bills_by_date(dash_date)
        all_menu         = db.MenuDB.get_all()
        _sp, _           = _get_save_location()
        missing_receipts = db.BillService.find_missing_receipts(
            primary_folder=_sp,
            backup_folder=CFG.bills_folder,
            work_date=dash_date,
        )
        available_dates = db.BillService.get_available_dates()

        def _on_dash_date_change(new_date: str) -> None:
            st.session_state[_dash_date_key] = new_date
            st.rerun()

        def _on_add_token(label: str, token_type: str) -> None:
            ok, msg = db.TokenService.add_token(label, token_type, CFG.token_max)
            if ok:
                st.rerun()
            else:
                st.session_state["_token_add_error"] = msg

        def _on_toggle_token(token_id: int, enabled: bool) -> None:
            db.TokenService.set_enabled(token_id, enabled)
            st.rerun()

        def _on_rename_token(token_id: int, label: str) -> None:
            db.TokenService.update_label(token_id, label)
            st.rerun()

        def _on_menu_add(name: str, price: float, category: str) -> None:
            db.MenuDB.add(name, price, category)
            st.rerun()

        def _on_menu_price(item_id: str, price: float) -> None:
            db.MenuDB.update_price(item_id, price)
            st.rerun()

        def _on_menu_toggle(item_id: str, available: bool) -> None:
            db.MenuDB.set_available(item_id, available)
            st.rerun()

        def _on_menu_delete(item_id: str) -> None:
            db.MenuDB.delete(item_id)
            st.rerun()

        def _on_save_settings(updates: dict[str, Any]) -> None:
            cfg_module.save(updates)
            new_count  = updates.get("token_count")
            new_prefix = updates.get("token_label_prefix", CFG.token_label_prefix)
            new_max    = updates.get("token_max", CFG.token_max)
            if new_count:
                db.TokenService.bootstrap_tokens(
                    int(new_count), new_prefix, int(new_max)
                )
            st.success("Settings saved.")
            st.rerun()

        def _on_dev_login_attempt(password: str) -> None:
            if _dev_creds.verify(password):
                st.session_state.authenticated_dev = True
                st.session_state.dev_authed_at     = datetime.now()
                st.rerun()
            else:
                st.session_state["_dev_login_error"] = True

        ui.owner_dashboard_ui(
            total_bills=total_bills,
            total_revenue=total_revenue,
            recent_bills=recent_bills,
            missing_receipts=missing_receipts,
            all_tokens=db.TokenService.get_all_including_disabled(),
            all_menu=all_menu,
            available_dates=available_dates,
            dash_date=dash_date,
            today=_TODAY,
            token_count=db.TokenService.count(),
            token_max=CFG.token_max,
            settings=cfg_module.load(),
            settings_defaults=cfg_module.DEFAULTS,
            currency=CFG.currency_symbol,
            token_types=CFG.token_types_enabled,
            dev_session_valid=_dev_session_valid(),
            dev_session_timeout=CFG.dev_session_timeout_mins,
            on_logout=_logout_owner,
            on_dash_date_change=_on_dash_date_change,
            on_add_token=_on_add_token,
            on_toggle_token=_on_toggle_token,
            on_rename_token=_on_rename_token,
            on_menu_add=_on_menu_add,
            on_menu_price=_on_menu_price,
            on_menu_toggle=_on_menu_toggle,
            on_menu_delete=_on_menu_delete,
            on_save_settings=_on_save_settings,
            on_dev_login_attempt=_on_dev_login_attempt,
            on_dev_logout=_logout_dev,
            token_add_error=st.session_state.pop("_token_add_error", None),
            dev_login_error=st.session_state.pop("_dev_login_error", False),
        )
        st.stop()

    # ── Cashier interface ─────────────────────────────────────────────────────
    if not all_tokens:
        st.warning("No tokens configured. Ask the owner to add tokens in the dashboard.")
        st.stop()

    if st.session_state.work_date < _TODAY and db.OrderService.has_any_open_orders():
        st.warning(
            f"⚠️ Working date is **{st.session_state.work_date}**. "
            "Clear or pay all open orders to reset to today."
        )

    selected_token_id: int = st.session_state.selected_token
    selected_token_row     = db.TokenService.get(selected_token_id)

    if selected_token_row is None:
        st.error("Selected token not found. Please choose another.")
        st.stop()

    menu_items    = db.MenuDB.get_all(available_only=True)
    current_items = db.OrderService.get_items(selected_token_id)

    tab1, = st.tabs(["🧾 Billing"])

    with tab1:
        col1, col2 = st.columns([2, 1])

        with col1:

            def _handle_delete(order_line_id: int) -> None:
                try:
                    db.OrderService.remove_item(order_line_id)
                    st.rerun()
                except Exception as exc:
                    st.error(f"Could not remove item: {exc}")

            def _handle_payment(
                items: list[dict[str, Any]],
                total: float,
                payment_method: str,
            ) -> None:
                try:
                    token = db.TokenService.get(selected_token_id)
                    if token is None:
                        st.error("Token not found.")
                        return
                    work_date = st.session_state.work_date
                    bill_id   = db.BillService.close_bill(
                        token_id=selected_token_id,
                        token_label=token["label"],
                        token_type=token["type"],
                        items=items,
                        total=total,
                        work_date=work_date,
                        payment_method=payment_method,
                    )
                    if CFG.save_csv_receipt:
                        if platform.system() == "Windows":
                            filename    = f"bill_{work_date}_{bill_id[:8]}.csv"
                            csv_content = db.BillService.build_csv_content(bill_id)
                            st.session_state.last_bill_download = {
                                "csv":      csv_content,
                                "filename": filename,
                                "bill_id":  bill_id,
                                "label":    token["label"],
                            }
                            db.BillService.update_filename(bill_id, filename)
                        else:
                            _, filename, _ = _write_csv_receipt(
                                bill_id, token["label"], items,
                                total, payment_method, work_date,
                            )
                            db.BillService.update_filename(bill_id, filename)
                    db.OrderService.clear_token(selected_token_id)
                    st.session_state.confirm_payment = False
                    st.success(
                        f"✅ Payment recorded — Bill #{bill_id[:8].upper()} "
                        f"· {work_date}"
                    )
                    st.rerun()
                except Exception as exc:
                    st.error(f"Payment failed: {exc}")

            def _set_confirm(val: bool) -> None:
                st.session_state.confirm_payment = val

            ui.bill_view(
                token=selected_token_row,
                items=current_items,
                currency=CFG.currency_symbol,
                payment_methods=CFG.payment_methods,
                confirm_before_payment=CFG.confirm_before_payment,
                on_delete=_handle_delete,
                on_payment=_handle_payment,
                confirm_state=st.session_state.confirm_payment,
                set_confirm=_set_confirm,
                pending_download=st.session_state.pop("last_bill_download", None),
                work_date=st.session_state.work_date,
            )

        with col2:

            def _handle_add_to_bill(item: dict[str, Any], qty: int) -> None:
                if qty <= 0:
                    st.error("Quantity must be positive.")
                    return
                db.OrderService.add_item(
                    token_id=selected_token_id,
                    item_name=item["name"],
                    unit_price=float(item["price"]),
                    quantity=qty,
                    category=item.get("category", ""),
                    item_id=item.get("item_id"),
                )
                st.rerun()

            ui.item_selector(
                menu_items=menu_items,
                token_id=selected_token_id,
                currency=CFG.currency_symbol,
                on_add=_handle_add_to_bill,
            )

    ui.fancy_footer(CFG.cafe_name)


# ──────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ──────────────────────────────────────────────────────────────────────────────

_render()
