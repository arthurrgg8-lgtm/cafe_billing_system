"""
ui.py — CafeBoss UI Layer
All visual components for the billing system.
Aesthetic: warm industrial espresso bar — dark roast palette, monospaced receipts,
           gold accents, tactile textures, confident typography.
"""

from __future__ import annotations

from typing import Any, Callable

import pandas as pd
import streamlit as st

# ======================================================
# CSS
# ======================================================

def load_fancy_css() -> None:
    """Inject global CSS. Call once at the top of app.py before any widgets."""
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=IBM+Plex+Mono:wght@400;600&family=DM+Sans:wght@300;400;500&display=swap');

        /* ---- ROOT PALETTE ------------------------------------------- */
        :root {
            --espresso:   #1a1007;
            --roast:      #2d1f0e;
            --mahogany:   #3d2b1a;
            --caramel:    #c07c3a;
            --gold:       #e0a84b;
            --cream:      #f5ead8;
            --parchment:  #fdf6eb;
            --steam:      #8a7566;
            --ink:        #221409;
            --success:    #4a7c59;
            --danger:     #8b2e2e;
            --radius:     6px;
        }

        /* ---- BASE ---------------------------------------------------- */
        html, body, [data-testid="stAppViewContainer"] {
            background: var(--roast) !important;
            color: var(--cream) !important;
            font-family: 'DM Sans', sans-serif !important;
        }

        /* Noise texture overlay */
        [data-testid="stAppViewContainer"]::before {
            content: '';
            position: fixed;
            inset: 0;
            background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='300' height='300'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3CfeColorMatrix type='saturate' values='0'/%3E%3C/filter%3E%3Crect width='300' height='300' filter='url(%23noise)' opacity='0.04'/%3E%3C/svg%3E");
            pointer-events: none;
            z-index: 0;
        }

        /* ---- SIDEBAR ------------------------------------------------- */
        [data-testid="stSidebar"] {
            background: var(--espresso) !important;
            border-right: 1px solid var(--mahogany) !important;
        }

        [data-testid="stSidebar"] * {
            color: var(--cream) !important;
        }

        /* ---- BUTTONS ------------------------------------------------- */
        .stButton > button {
            font-family: 'IBM Plex Mono', monospace !important;
            font-size: 0.75rem !important;
            font-weight: 600 !important;
            letter-spacing: 0.08em !important;
            text-transform: uppercase !important;
            background: var(--mahogany) !important;
            color: var(--gold) !important;
            border: 1px solid var(--caramel) !important;
            border-radius: var(--radius) !important;
            padding: 0.45rem 1rem !important;
            transition: all 0.15s ease !important;
            box-shadow: 0 2px 8px rgba(0,0,0,0.4) !important;
        }

        .stButton > button:hover {
            background: var(--caramel) !important;
            color: var(--espresso) !important;
            border-color: var(--gold) !important;
            transform: translateY(-1px) !important;
            box-shadow: 0 4px 14px rgba(224,168,75,0.25) !important;
        }

        /* Primary variant (used for pay/confirm) */
        .stButton > button[kind="primary"] {
            background: var(--gold) !important;
            color: var(--espresso) !important;
            border-color: var(--gold) !important;
        }

        /* ---- INPUTS -------------------------------------------------- */
        .stTextInput input,
        .stNumberInput input,
        .stSelectbox select,
        .stSelectbox > div > div {
            background: var(--espresso) !important;
            color: var(--cream) !important;
            border: 1px solid var(--mahogany) !important;
            border-radius: var(--radius) !important;
            font-family: 'DM Sans', sans-serif !important;
        }

        .stTextInput input:focus,
        .stNumberInput input:focus {
            border-color: var(--caramel) !important;
            box-shadow: 0 0 0 2px rgba(192,124,58,0.2) !important;
        }

        /* ---- TABS ---------------------------------------------------- */
        .stTabs [data-baseweb="tab-list"] {
            background: var(--espresso) !important;
            border-radius: var(--radius) var(--radius) 0 0 !important;
            border-bottom: 2px solid var(--caramel) !important;
            gap: 0 !important;
        }

        .stTabs [data-baseweb="tab"] {
            font-family: 'IBM Plex Mono', monospace !important;
            font-size: 0.72rem !important;
            font-weight: 600 !important;
            letter-spacing: 0.1em !important;
            text-transform: uppercase !important;
            color: var(--steam) !important;
            padding: 0.6rem 1.4rem !important;
            border-radius: 0 !important;
        }

        .stTabs [aria-selected="true"] {
            background: var(--mahogany) !important;
            color: var(--gold) !important;
            border-bottom: 2px solid var(--gold) !important;
        }

        /* ---- DATAFRAME / TABLE --------------------------------------- */
        .stDataFrame, [data-testid="stDataFrameContainer"] {
            background: var(--espresso) !important;
            border: 1px solid var(--mahogany) !important;
            border-radius: var(--radius) !important;
        }

        /* ---- METRIC -------------------------------------------------- */
        [data-testid="stMetric"] {
            background: var(--espresso) !important;
            border: 1px solid var(--mahogany) !important;
            border-radius: var(--radius) !important;
            padding: 1rem !important;
        }

        [data-testid="stMetricLabel"] {
            font-family: 'IBM Plex Mono', monospace !important;
            font-size: 0.65rem !important;
            letter-spacing: 0.12em !important;
            text-transform: uppercase !important;
            color: var(--steam) !important;
        }

        [data-testid="stMetricValue"] {
            font-family: 'Playfair Display', serif !important;
            font-size: 2rem !important;
            color: var(--gold) !important;
        }

        /* ---- ALERTS -------------------------------------------------- */
        .stAlert {
            border-radius: var(--radius) !important;
            font-family: 'IBM Plex Mono', monospace !important;
            font-size: 0.78rem !important;
        }

        /* ---- DIVIDER ------------------------------------------------- */
        hr {
            border-color: var(--mahogany) !important;
        }

        /* ---- SCROLLBAR ----------------------------------------------- */
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: var(--espresso); }
        ::-webkit-scrollbar-thumb { background: var(--mahogany); border-radius: 3px; }
        ::-webkit-scrollbar-thumb:hover { background: var(--caramel); }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ======================================================
# HEADER / FOOTER
# ======================================================

def fancy_header() -> None:
    st.markdown(
        """
        <div style="
            display:flex; align-items:center; gap:14px;
            padding: 1.2rem 0 0.6rem;
            border-bottom: 2px solid #3d2b1a;
            margin-bottom: 1.4rem;
        ">
            <span style="font-size:2.2rem; line-height:1;">☕</span>
            <div>
                <div style="
                    font-family:'Playfair Display',serif;
                    font-size:1.9rem; font-weight:900;
                    color:#e0a84b; letter-spacing:-0.01em; line-height:1;">
                    CafeBoss
                </div>
                <div style="
                    font-family:'IBM Plex Mono',monospace;
                    font-size:0.65rem; color:#8a7566;
                    letter-spacing:0.18em; text-transform:uppercase;
                    margin-top:1px;">
                    Modern Billing System
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def fancy_footer() -> None:
    st.markdown(
        """
        <div style="
            margin-top:3rem;
            padding-top:1rem;
            border-top:1px solid #3d2b1a;
            font-family:'IBM Plex Mono',monospace;
            font-size:0.6rem;
            color:#8a7566;
            letter-spacing:0.14em;
            text-align:center;
            text-transform:uppercase;
        ">
            CafeBoss &nbsp;·&nbsp; Billing System &nbsp;·&nbsp; Developed by AnuditKhatri
        </div>
        """,
        unsafe_allow_html=True,
    )


# ======================================================
# PASSWORD SETUP
# ======================================================

def password_setup_ui(on_save: Callable[[str], None]) -> None:
    """First-run password setup screen."""
    st.markdown(
        """
        <div style="max-width:420px; margin:4rem auto; text-align:center;">
            <div style="font-family:'Playfair Display',serif; font-size:2rem;
                        color:#e0a84b; margin-bottom:0.4rem;">
                ☕ Welcome to CafeBoss
            </div>
            <div style="font-family:'IBM Plex Mono',monospace; font-size:0.7rem;
                        color:#8a7566; letter-spacing:0.15em; text-transform:uppercase;
                        margin-bottom:2rem;">
                Set your owner password to get started
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form("setup_password_form"):
        st.markdown(
            "<p style='font-family:IBM Plex Mono,monospace; font-size:0.72rem;"
            " color:#8a7566; letter-spacing:0.1em; text-transform:uppercase;"
            " margin-bottom:4px;'>New Password</p>",
            unsafe_allow_html=True,
        )
        pw1 = st.text_input("", type="password", key="setup_pw1", label_visibility="collapsed")
        st.markdown(
            "<p style='font-family:IBM Plex Mono,monospace; font-size:0.72rem;"
            " color:#8a7566; letter-spacing:0.1em; text-transform:uppercase;"
            " margin-bottom:4px; margin-top:8px;'>Confirm Password</p>",
            unsafe_allow_html=True,
        )
        pw2 = st.text_input("", type="password", key="setup_pw2", label_visibility="collapsed")
        submitted = st.form_submit_button("Set Password", use_container_width=True)

    if submitted:
        if pw1 != pw2:
            st.error("Passwords do not match.")
        else:
            try:
                on_save(pw1)
                st.success("Password set! Reloading…")
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))


# ======================================================
# OWNER LOGIN
# ======================================================

def owner_login_ui() -> str | None:
    """
    Renders the owner login modal.
    Returns the submitted password string, or None if not yet submitted.
    """
    st.markdown(
        """
        <div style="
            background:#1a1007;
            border:1px solid #3d2b1a;
            border-radius:8px;
            padding:2rem;
            max-width:380px;
            margin:2rem auto;
        ">
            <div style="font-family:'Playfair Display',serif; font-size:1.4rem;
                        color:#e0a84b; margin-bottom:1.2rem; text-align:center;">
                👑 Owner Access
            </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form("owner_login_form"):
        st.markdown(
            "<p style='font-family:IBM Plex Mono,monospace; font-size:0.7rem;"
            " color:#8a7566; letter-spacing:0.12em; text-transform:uppercase;'>Password</p>",
            unsafe_allow_html=True,
        )
        password = st.text_input("", type="password", key="owner_pw_input", label_visibility="collapsed")
        cols = st.columns(2)
        with cols[0]:
            submitted = st.form_submit_button("Unlock", use_container_width=True)
        with cols[1]:
            cancelled = st.form_submit_button("Cancel", use_container_width=True)

    st.markdown("</div>", unsafe_allow_html=True)

    if cancelled:
        st.session_state.show_owner_login = False
        st.rerun()

    if submitted and password:
        return password
    return None


# ======================================================
# SIDEBAR COMPONENTS
# ======================================================

def token_board(
    selected_token: int,
    token_status: dict[int, bool],
    on_token_click: Callable[[int], None],
) -> None:
    """Token selector displayed in the sidebar."""
    st.markdown(
        "<div style='font-family:IBM Plex Mono,monospace; font-size:0.62rem;"
        " color:#8a7566; letter-spacing:0.18em; text-transform:uppercase;"
        " margin-bottom:0.8rem;'>Tokens</div>",
        unsafe_allow_html=True,
    )

    tokens = list(token_status.keys())
    rows = [tokens[i : i + 5] for i in range(0, len(tokens), 5)]

    for row in rows:
        cols = st.columns(len(row))
        for col, token in zip(cols, row):
            with col:
                active = token == selected_token
                occupied = token_status[token]

                if occupied and not active:
                    label = f"🟠 {token}"
                elif active:
                    label = f"✅ {token}"
                else:
                    label = f"⬜ {token}"

                if st.button(label, key=f"token_btn_{token}", use_container_width=True):
                    on_token_click(token)


def save_location_info(path: str, label: str) -> None:
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown(
        f"""
        <div style="font-family:'IBM Plex Mono',monospace; font-size:0.62rem;
                    color:#8a7566; letter-spacing:0.1em;">
            <div style="text-transform:uppercase; margin-bottom:3px;">Save Location</div>
            <div style="color:#c07c3a;">{label}</div>
            <div style="color:#5a4a3a; font-size:0.55rem; word-break:break-all;
                        margin-top:2px;">{path}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("<hr>", unsafe_allow_html=True)


# ======================================================
# BILLING TAB
# ======================================================

def bill_view(
    token: int,
    items: list[dict[str, Any]],
    on_delete: Callable[[int], None],
    on_payment: Callable[[list[dict[str, Any]], float], None],
    confirm_payment: bool,
    set_confirm: Callable[[bool], None],
) -> None:
    """Left column of the Billing tab: shows current order and payment controls."""

    # Receipt header
    st.markdown(
        f"""
        <div style="
            font-family:'IBM Plex Mono',monospace;
            background:#1a1007;
            border:1px solid #3d2b1a;
            border-radius:6px 6px 0 0;
            padding:0.7rem 1rem;
            display:flex; justify-content:space-between; align-items:center;
        ">
            <span style="font-size:0.7rem; letter-spacing:0.15em;
                         text-transform:uppercase; color:#8a7566;">Receipt</span>
            <span style="font-size:0.75rem; color:#e0a84b; font-weight:600;">
                Token #{token}
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not items:
        st.markdown(
            """
            <div style="
                background:#1a1007; border:1px solid #3d2b1a; border-top:none;
                border-radius:0 0 6px 6px; padding:2.5rem; text-align:center;
            ">
                <div style="font-size:2rem; margin-bottom:0.5rem;">🍃</div>
                <div style="font-family:'IBM Plex Mono',monospace; font-size:0.7rem;
                            color:#5a4a3a; letter-spacing:0.12em; text-transform:uppercase;">
                    No items yet
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    # Item rows
    st.markdown(
        "<div style='background:#1a1007; border:1px solid #3d2b1a; border-top:none; padding:0.5rem 0;'>",
        unsafe_allow_html=True,
    )

    total = 0.0
    for idx, item in enumerate(items):
        subtotal = item["Subtotal"]
        total += subtotal
        col_info, col_del = st.columns([5, 1])
        with col_info:
            st.markdown(
                f"""
                <div style="
                    padding:0.4rem 1rem;
                    border-bottom:1px solid #2d1f0e;
                    font-family:'IBM Plex Mono',monospace; font-size:0.75rem;
                ">
                    <span style="color:#f5ead8;">{item['Item']}</span>
                    <span style="color:#5a4a3a;"> × {item['Quantity']}</span>
                    <span style="float:right; color:#e0a84b;">
                        ₹{subtotal:,.2f}
                    </span>
                    <span style="float:right; color:#5a4a3a; margin-right:1rem;">
                        @₹{item['Price']}
                    </span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with col_del:
            if st.button("✕", key=f"del_{token}_{idx}", help="Remove item"):
                on_delete(idx)

    st.markdown("</div>", unsafe_allow_html=True)

    # Total bar
    st.markdown(
        f"""
        <div style="
            background:#2d1f0e; border:1px solid #3d2b1a; border-top:none;
            border-radius:0 0 6px 6px;
            padding:0.8rem 1rem;
            font-family:'IBM Plex Mono',monospace;
            display:flex; justify-content:space-between; align-items:center;
        ">
            <span style="font-size:0.7rem; letter-spacing:0.15em;
                         text-transform:uppercase; color:#8a7566;">Total</span>
            <span style="font-size:1.3rem; font-weight:700; color:#e0a84b;">
                ₹{total:,.2f}
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.write("")

    # Payment flow
    if not confirm_payment:
        if st.button("💳 Process Payment", use_container_width=True, type="primary"):
            set_confirm(True)
            st.rerun()
    else:
        st.warning(f"Confirm payment of **₹{total:,.2f}** for Token #{token}?")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("✅ Confirm", use_container_width=True, type="primary"):
                set_confirm(False)
                on_payment(items, total)
        with c2:
            if st.button("❌ Cancel", use_container_width=True):
                set_confirm(False)
                st.rerun()


def item_selector(
    menu_df: pd.DataFrame,
    token: int,
    on_add: Callable[[str, float, int], None],
) -> None:
    """Right column of the Billing tab: pick items from the menu to add."""
    st.markdown(
        """
        <div style="font-family:'IBM Plex Mono',monospace; font-size:0.62rem;
                    color:#8a7566; letter-spacing:0.18em; text-transform:uppercase;
                    margin-bottom:0.6rem;">Add Items</div>
        """,
        unsafe_allow_html=True,
    )

    if menu_df.empty:
        st.info("No menu items found. Add items in the Menu tab.")
        return

    categories = ["All"] + sorted(menu_df["Category"].dropna().unique().tolist())
    selected_cat = st.selectbox("Category", categories, key=f"cat_filter_{token}")

    filtered = menu_df if selected_cat == "All" else menu_df[menu_df["Category"] == selected_cat]

    if filtered.empty:
        st.caption("No items in this category.")
        return

    item_options = filtered["Item"].tolist()
    selected_item = st.selectbox("Item", item_options, key=f"item_select_{token}")

    item_row = filtered[filtered["Item"] == selected_item].iloc[0]
    price = float(item_row["Price"])

    st.markdown(
        f"<div style='font-family:IBM Plex Mono,monospace; font-size:0.8rem;"
        f" color:#c07c3a; margin:4px 0;'>₹{price:,.2f}</div>",
        unsafe_allow_html=True,
    )

    qty = st.number_input("Quantity", min_value=1, value=1, step=1, key=f"qty_{token}")

    if st.button("＋ Add to Bill", use_container_width=True, key=f"add_{token}"):
        on_add(selected_item, price, int(qty))


# ======================================================
# MENU MANAGEMENT TAB
# ======================================================

def menu_view(
    menu_df: pd.DataFrame,
    on_add: Callable[[str, float, str], None],
    on_update_price: Callable[[int, float], None],
    on_delete: Callable[[int], None],
) -> None:
    """Full Menu tab: view, add, edit, delete menu items."""

    left, right = st.columns([3, 2])

    with left:
        st.markdown(
            "<div style='font-family:IBM Plex Mono,monospace; font-size:0.62rem;"
            " color:#8a7566; letter-spacing:0.18em; text-transform:uppercase;"
            " margin-bottom:0.6rem;'>Current Menu</div>",
            unsafe_allow_html=True,
        )

        if menu_df.empty:
            st.info("Menu is empty. Add your first item →")
        else:
            # Display each item with inline edit / delete
            for idx, row in menu_df.iterrows():
                with st.expander(
                    f"**{row['Item']}** — ₹{row['Price']:,.2f}   `{row.get('Category','—')}`",
                    expanded=False,
                ):
                    new_price = st.number_input(
                        "Update Price (₹)",
                        value=float(row["Price"]),
                        min_value=0.01,
                        key=f"edit_price_{idx}",
                    )
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("💾 Save Price", key=f"save_{idx}", use_container_width=True):
                            try:
                                on_update_price(int(idx), new_price)
                                st.success("Price updated.")
                                st.rerun()
                            except (IndexError, ValueError) as exc:
                                st.error(str(exc))
                    with c2:
                        if st.button("🗑 Delete", key=f"delete_{idx}", use_container_width=True):
                            try:
                                on_delete(int(idx))
                                st.success("Item deleted.")
                                st.rerun()
                            except IndexError as exc:
                                st.error(str(exc))

    with right:
        st.markdown(
            "<div style='font-family:IBM Plex Mono,monospace; font-size:0.62rem;"
            " color:#8a7566; letter-spacing:0.18em; text-transform:uppercase;"
            " margin-bottom:0.6rem;'>Add New Item</div>",
            unsafe_allow_html=True,
        )

        with st.form("add_menu_item_form", clear_on_submit=True):
            name = st.text_input("Item Name")
            price = st.number_input("Price (₹)", min_value=0.01, value=50.0, step=0.50)
            category = st.text_input("Category", value="Beverages")
            submitted = st.form_submit_button("Add Item", use_container_width=True)

        if submitted:
            try:
                on_add(name.strip(), price, category.strip())
                st.success(f"'{name}' added to menu.")
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))


# ======================================================
# OWNER DASHBOARD
# ======================================================

def owner_dashboard_ui(
    total_bills: int,
    total_revenue: float,
    recent_bills: list[dict[str, Any]],
    missing_files: list[dict[str, Any]],
    on_logout: Callable[[], None],
    on_download_report: Callable[[], None],
) -> None:
    """Full owner dashboard view."""

    # Header row
    head_left, head_right = st.columns([4, 1])
    with head_left:
        st.markdown(
            """
            <div style="font-family:'Playfair Display',serif; font-size:1.6rem;
                        color:#e0a84b; margin-bottom:0.2rem;">
                👑 Owner Dashboard
            </div>
            <div style="font-family:'IBM Plex Mono',monospace; font-size:0.62rem;
                        color:#8a7566; letter-spacing:0.15em; text-transform:uppercase;">
                Today's summary
            </div>
            """,
            unsafe_allow_html=True,
        )
    with head_right:
        if st.button("🔒 Logout", use_container_width=True):
            on_logout()

    st.markdown("<hr>", unsafe_allow_html=True)

    # KPI metrics
    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("Bills Today", total_bills)
    with m2:
        st.metric("Revenue Today (₹)", f"{total_revenue:,.2f}")
    with m3:
        integrity = "⚠️ Issues Found" if missing_files else "✅ All Good"
        st.metric("File Integrity", integrity)

    st.markdown("<hr>", unsafe_allow_html=True)

    # Missing files warning
    if missing_files:
        st.error(f"⚠️ {len(missing_files)} bill file(s) referenced in audit log but not found on disk:")
        df_missing = pd.DataFrame(missing_files)
        st.dataframe(df_missing, use_container_width=True)
        st.markdown("<hr>", unsafe_allow_html=True)

    # Transaction log
    st.markdown(
        "<div style='font-family:IBM Plex Mono,monospace; font-size:0.62rem;"
        " color:#8a7566; letter-spacing:0.18em; text-transform:uppercase;"
        " margin-bottom:0.6rem;'>Transaction Log</div>",
        unsafe_allow_html=True,
    )

    if not recent_bills:
        st.info("No transactions recorded today.")
    else:
        df_bills = pd.DataFrame(recent_bills)
        st.dataframe(df_bills, use_container_width=True, hide_index=True)
