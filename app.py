import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
import hashlib
import csv
import platform
import secrets
import ui

# ======================================================
# PAGE CONFIG
# ======================================================

st.set_page_config(
    page_title="CafeBoss - Modern Billing System",
    page_icon="☕",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ======================================================
# SESSION STATE INIT
# ======================================================

DEFAULT_TOKENS = 10

if 'authenticated_owner' not in st.session_state:
    st.session_state.authenticated_owner = False

if 'token_status' not in st.session_state:
    st.session_state.token_status = {i: False for i in range(1, DEFAULT_TOKENS + 1)}

if 'token_items' not in st.session_state:
    st.session_state.token_items = {i: [] for i in range(1, DEFAULT_TOKENS + 1)}

if 'selected_token' not in st.session_state:
    st.session_state.selected_token = 1

if 'show_owner_login' not in st.session_state:
    st.session_state.show_owner_login = False

if 'confirm_payment' not in st.session_state:
    st.session_state.confirm_payment = False

# ======================================================
# FILE PATHS
# ======================================================

MENU_FILE = "menu_items.csv"
AUDIT_FOLDER = "audit_logs"
BILLS_FOLDER = "bills"
PASSWORD_FILE = "owner_password.hash"
PASSWORD_EXPIRY_FILE = "password_expiry.txt"

os.makedirs(AUDIT_FOLDER, exist_ok=True)
os.makedirs(BILLS_FOLDER, exist_ok=True)

# Initialize Menu File
if not os.path.exists(MENU_FILE):
    pd.DataFrame(columns=["Item", "Price", "Category"]).to_csv(MENU_FILE, index=False)

# ======================================================
# SECURITY FUNCTIONS
# ======================================================

def hash_password(password, salt=None):
    if salt is None:
        salt = secrets.token_hex(16)
    hashed = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}${hashed}"

def verify_password(password, stored_value):
    try:
        salt, hashed = stored_value.split("$")
        return hash_password(password, salt) == stored_value
    except Exception:
        return False

def save_password(password):
    if len(password) < 6:
        raise ValueError("Password must be at least 6 characters.")
    hashed = hash_password(password)
    with open(PASSWORD_FILE, 'w') as f:
        f.write(hashed)
    expiry = datetime.now() + timedelta(days=30)
    with open(PASSWORD_EXPIRY_FILE, 'w') as f:
        f.write(expiry.strftime("%Y-%m-%d"))

def check_password_exists():
    return os.path.exists(PASSWORD_FILE)

# ======================================================
# BILLING FUNCTIONS
# ======================================================

def get_save_location():
    system = platform.system()
    if system == "Windows":
        downloads = os.path.join(os.path.expanduser("~"), "Downloads")
        if os.path.exists(downloads):
            return downloads, "Downloads"
    return os.path.abspath(BILLS_FOLDER), "Bills Folder"

def save_bill(token, items, total):
    if not items or total <= 0:
        raise ValueError("Invalid bill data.")

    save_path, location_desc = get_save_location()
    os.makedirs(save_path, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"token{token}_{timestamp}.csv"
    filepath = os.path.join(save_path, filename)

    try:
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Token", "Item", "Quantity", "Unit Price", "Subtotal"])
            for item in items:
                writer.writerow([
                    token,
                    item["Item"],
                    item["Quantity"],
                    item["Price"],
                    item["Subtotal"]
                ])
            writer.writerow(["", "", "", "TOTAL", total])
            writer.writerow(["", "", "", "PAID AT", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])

        # Backup copy
        backup_path = os.path.join(BILLS_FOLDER, filename)
        with open(backup_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Token", "Item", "Quantity", "Unit Price", "Subtotal"])
            for item in items:
                writer.writerow([
                    token,
                    item["Item"],
                    item["Quantity"],
                    item["Price"],
                    item["Subtotal"]
                ])
            writer.writerow(["", "", "", "TOTAL", total])

    except Exception as e:
        raise RuntimeError(f"Bill saving failed: {e}")

    return filepath, filename, location_desc

def save_to_audit_log(token, items, total, filename):
    today = datetime.now().strftime("%Y-%m-%d")
    audit_file = os.path.join(AUDIT_FOLDER, f"audit_{today}.csv")
    file_exists = os.path.isfile(audit_file)

    try:
        with open(audit_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["Timestamp", "Token", "Total", "Filename", "Item_Count"])
            writer.writerow([
                datetime.now().strftime("%H:%M:%S"),
                token,
                total,
                filename,
                len(items)
            ])
    except Exception as e:
        raise RuntimeError(f"Audit logging failed: {e}")

def reset_token(token):
    if token in st.session_state.token_items:
        st.session_state.token_items[token].clear()
    st.session_state.token_status[token] = False

# ======================================================
# OWNER DASHBOARD FUNCTIONS
# ======================================================

def get_owner_dashboard_data():
    today = datetime.now().strftime("%Y-%m-%d")
    audit_file = os.path.join(AUDIT_FOLDER, f"audit_{today}.csv")

    total_bills = 0
    total_revenue = 0
    bills_list = []

    if os.path.exists(audit_file):
        df = pd.read_csv(audit_file)
        total_bills = len(df)
        total_revenue = df["Total"].sum()
        bills_list = df.to_dict("records")

    return total_bills, total_revenue, bills_list

def verify_transactions():
    today = datetime.now().strftime("%Y-%m-%d")
    audit_file = os.path.join(AUDIT_FOLDER, f"audit_{today}.csv")
    save_path, _ = get_save_location()

    missing = []

    if os.path.exists(audit_file):
        df = pd.read_csv(audit_file)
        for _, row in df.iterrows():
            filename = row["Filename"]
            if not (
                os.path.exists(os.path.join(save_path, filename)) or
                os.path.exists(os.path.join(BILLS_FOLDER, filename))
            ):
                missing.append(row.to_dict())

    return missing

# ======================================================
# MENU MANAGEMENT
# ======================================================

def load_menu():
    return pd.read_csv(MENU_FILE)

def save_menu(df):
    df.to_csv(MENU_FILE, index=False)

def add_menu_item(name, price, category):
    if not name or price <= 0:
        raise ValueError("Invalid menu item.")
    df = load_menu()
    new_row = pd.DataFrame({"Item": [name], "Price": [price], "Category": [category]})
    df = pd.concat([df, new_row], ignore_index=True)
    save_menu(df)

def update_menu_price(idx, new_price):
    df = load_menu()
    if 0 <= idx < len(df):
        df.at[idx, "Price"] = new_price
        save_menu(df)

def delete_menu_item(idx):
    df = load_menu()
    if 0 <= idx < len(df):
        df = df.drop(idx).reset_index(drop=True)
        save_menu(df)

# ======================================================
# PASSWORD SETUP
# ======================================================

if not check_password_exists():
    ui.load_fancy_css()
    ui.password_setup_ui(save_password)
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
        on_token_click=lambda token: setattr(st.session_state, 'selected_token', token) or st.rerun()
    )

    save_path, loc = get_save_location()
    ui.save_location_info(save_path, loc)

    if st.button("👑 OWNER DASHBOARD", use_container_width=True):
        st.session_state.show_owner_login = True
        st.rerun()

# Owner Login
if st.session_state.get('show_owner_login', False) and not st.session_state.authenticated_owner:
    password = ui.owner_login_ui()
    if password:
        with open(PASSWORD_FILE, 'r') as f:
            stored = f.read().strip()
        if verify_password(password, stored):
            st.session_state.authenticated_owner = True
            st.session_state.show_owner_login = False
            st.rerun()
        else:
            st.error("Invalid password")

# Owner Dashboard
if st.session_state.authenticated_owner:
    total_bills, total_revenue, recent_bills = get_owner_dashboard_data()
    missing_files = verify_transactions()

    ui.owner_dashboard_ui(
        total_bills,
        total_revenue,
        recent_bills,
        missing_files,
        on_logout=lambda: setattr(st.session_state, 'authenticated_owner', False) or st.rerun(),
        on_download_report=lambda: None
    )
    st.stop()

# ======================================================
# CASHIER INTERFACE
# ======================================================

selected_token = st.session_state.selected_token
menu_df = load_menu()

tab1, tab2 = st.tabs(["🧾 Billing", "📋 Menu"])

with tab1:
    col1, col2 = st.columns([2, 1])

    with col1:

        def handle_delete(idx):
            try:
                st.session_state.token_items[selected_token].pop(idx)
                if not st.session_state.token_items[selected_token]:
                    st.session_state.token_status[selected_token] = False
                st.rerun()
            except Exception:
                st.error("Failed to remove item.")

        def handle_payment(items, total):
            try:
                path, name, loc = save_bill(selected_token, items, total)
                save_to_audit_log(selected_token, items, total, name)

                reset_token(selected_token)

                st.success("Payment successful.")
                st.rerun()
            except Exception as e:
                st.error(str(e))

        def set_confirm(val):
            st.session_state.confirm_payment = val

        ui.bill_view(
            selected_token,
            st.session_state.token_items[selected_token],
            handle_delete,
            handle_payment,
            st.session_state.confirm_payment,
            set_confirm
        )

    with col2:

        def handle_add_to_bill(name, price, qty):
            if qty <= 0:
                st.error("Quantity must be positive.")
                return
            st.session_state.token_items[selected_token].append({
                "Item": name,
                "Price": price,
                "Quantity": qty,
                "Subtotal": price * qty
            })
            st.session_state.token_status[selected_token] = True
            st.rerun()

        ui.item_selector(menu_df, selected_token, handle_add_to_bill)

with tab2:
    ui.menu_view(
        menu_df,
        add_menu_item,
        update_menu_price,
        delete_menu_item
    )

ui.fancy_footer()