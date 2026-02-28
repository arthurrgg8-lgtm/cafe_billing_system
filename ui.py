import streamlit as st
import pandas as pd

# ==========================================
# GLOBAL CAFE THEME
# ==========================================

def load_fancy_css():
    st.markdown("""
    <style>
    /* Status Indicator Circles */
.free-indicator {
    width: 14px;
    height: 14px;
    border-radius: 50%;
    background-color: #2ecc71;
}

.occupied-indicator {
    width: 14px;
    height: 14px;
    border-radius: 50%;
    background-color: #e74c3c;
}

    /* Header */
    .header-title {
        font-size: 34px;
        font-weight: 700;
        color: #4b2e2e;
        margin-bottom: 5px;
    }

    /* Card Style */
    .card {
        background: white;
        padding: 20px;
        border-radius: 14px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        margin-bottom: 20px;
    }

    /* General Buttons */
    .stButton > button {
        border-radius: 10px;
        height: 48px;
        font-weight: 600;
        border: none;
    }

    /* Token Colors */
    .token-free button {
        background-color: #2ecc71 !important;
        color: white !important;
    }

    .token-occupied button {
        background-color: #e74c3c !important;
        color: white !important;
    }

    .token-selected button {
        border: 3px solid #2c3e50 !important;
    }

    /* Section Titles */
    .section-title {
        font-size: 22px;
        font-weight: 600;
        color: #3d2c29;
        margin-bottom: 10px;
    }

    /* Metrics */
    div[data-testid="stMetricValue"] {
        color: #4b2e2e;
        font-weight: 700;
    }
    </style>
    """, unsafe_allow_html=True)


# ==========================================
# HEADER & FOOTER
# ==========================================

def fancy_header():
    st.markdown("<div class='header-title'>☕ CafeBoss POS System</div>", unsafe_allow_html=True)
    st.markdown("<hr>", unsafe_allow_html=True)

def fancy_footer():
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("<center style='color:#6b4f4f;'>© 2026 CafeBoss | Developed by AnuditKhatri</center>", unsafe_allow_html=True)


# ==========================================
# PASSWORD SETUP
# ==========================================

def password_setup_ui(save_password_callback):
    st.markdown("<div class='section-title'>🔐 First Time Setup</div>", unsafe_allow_html=True)

    pwd1 = st.text_input("Create Owner Password", type="password")
    pwd2 = st.text_input("Confirm Password", type="password")

    if st.button("Save Password"):
        if pwd1 and pwd1 == pwd2:
            save_password_callback(pwd1)
            st.success("Password Created Successfully. Restart App.")
        else:
            st.error("Passwords do not match.")


def owner_login_ui():
    st.markdown("<div class='section-title'>👑 Owner Login</div>", unsafe_allow_html=True)
    return st.text_input("Enter Password", type="password")


# ==========================================
# TOKEN BOARD
# ==========================================

def token_board(selected_token, token_status, on_token_click):
    st.markdown("<div class='section-title'>🎟 Token Board</div>", unsafe_allow_html=True)

    for token in token_status:
        occupied = token_status[token]

        if occupied:
            status_text = "Occupied"
            color_class = "occupied-indicator"
            button_class = "token-occupied"
        else:
            status_text = "Free"
            color_class = "free-indicator"
            button_class = "token-free"

        if token == selected_token:
            button_class += " token-selected"

        with st.container():
            st.markdown(
                f"""
                <div class="{button_class}">
                    <div style="display:flex; align-items:center; gap:10px;">
                        <div class="{color_class}"></div>
                        <div style="font-weight:600;">
                            Token {token} • {status_text}
                        </div>
                    </div>
                """,
                unsafe_allow_html=True
            )

            if st.button("Select", key=f"token_{token}", use_container_width=True):
                on_token_click(token)

            st.markdown("</div>", unsafe_allow_html=True)


# ==========================================
# SAVE LOCATION INFO
# ==========================================

def save_location_info(path, loc):
    st.info(f"💾 Bills saving to: {loc}")


# ==========================================
# BILL VIEW
# ==========================================

def bill_view(token, items, on_delete, on_payment, confirm_payment, set_confirm):
    st.markdown(f"<div class='section-title'>🧾 Token {token} Bill</div>", unsafe_allow_html=True)

    if not items:
        st.warning("No items added.")
        return

    df = pd.DataFrame(items)
    st.dataframe(df, use_container_width=True)

    total = sum(item['Subtotal'] for item in items)
    st.markdown(f"### 💰 Total: ₹ {total:.2f}")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🗑 Remove Last Item"):
            on_delete(len(items) - 1)

    with col2:
        if not confirm_payment:
            if st.button("✅ Proceed to Payment", use_container_width=True):
                set_confirm(True)
        else:
            st.warning("Confirm Payment?")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("💵 Confirm"):
                    on_payment(items, total)
            with c2:
                if st.button("Cancel"):
                    set_confirm(False)


# ==========================================
# PAYMENT SUCCESS
# ==========================================

def payment_success_ui(content, filename, location):
    st.success("Payment Successful!")
    st.download_button(
        label="📥 Download Bill",
        data=content,
        file_name=filename,
        mime="text/csv"
    )
    st.info(f"Saved to: {location}")


# ==========================================
# ITEM SELECTOR
# ==========================================

def item_selector(menu_df, selected_token, on_add_to_bill):
    st.markdown("<div class='section-title'>➕ Add Items</div>", unsafe_allow_html=True)

    if menu_df.empty:
        st.warning("Menu is empty.")
        return

    item = st.selectbox("Select Item", menu_df["Item"])
    price = float(menu_df[menu_df["Item"] == item]["Price"].values[0])
    qty = st.number_input("Quantity", min_value=1, step=1)

    st.markdown(f"Price: ₹ {price}")

    if st.button("Add to Bill", use_container_width=True):
        on_add_to_bill(item, price, qty)


# ==========================================
# MENU MANAGEMENT
# ==========================================

def menu_view(menu_df, on_add_item, on_update_price, on_delete_item):
    st.markdown("<div class='section-title'>📋 Menu Management</div>", unsafe_allow_html=True)

    st.dataframe(menu_df, use_container_width=True)

    st.markdown("### ➕ Add New Item")
    name = st.text_input("Item Name")
    price = st.number_input("Price", min_value=0.0, step=1.0)
    category = st.text_input("Category")

    if st.button("Add Item"):
        if name:
            on_add_item(name, price, category)
            st.success("Item Added")
            st.rerun()

    if not menu_df.empty:
        st.markdown("### ✏ Update Price")
        idx = st.number_input("Item Index", min_value=0, max_value=len(menu_df)-1, step=1)
        new_price = st.number_input("New Price", min_value=0.0, step=1.0)

        if st.button("Update Price"):
            on_update_price(idx, new_price)
            st.success("Price Updated")
            st.rerun()

        st.markdown("### ❌ Delete Item")
        del_idx = st.number_input("Delete Item Index", min_value=0, max_value=len(menu_df)-1, step=1)

        if st.button("Delete Item"):
            on_delete_item(del_idx)
            st.success("Item Deleted")
            st.rerun()


# ==========================================
# OWNER DASHBOARD
# ==========================================

def owner_dashboard_ui(total_bills, total_revenue, recent_bills, missing_files, on_logout, on_download_report):
    st.markdown("<div class='section-title'>📊 Owner Dashboard</div>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    col1.metric("Total Bills Today", total_bills)
    col2.metric("Total Revenue Today", f"₹ {total_revenue:.2f}")

    st.markdown("### 🧾 Recent Transactions")
    if recent_bills:
        st.dataframe(pd.DataFrame(recent_bills), use_container_width=True)
    else:
        st.info("No transactions yet.")

    st.markdown("### ⚠ Missing Bills")
    if missing_files:
        st.dataframe(pd.DataFrame(missing_files), use_container_width=True)
    else:
        st.success("All transactions verified.")

    if st.button("🚪 Logout"):
        on_logout()