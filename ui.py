"""
ui.py — CafeBoss UI Layer
Pure rendering — no DB calls, no business logic.
Responsive for desktop, tablet, and mobile.

New in this version:
  - working_date_ui() — sidebar date widget with validation feedback
  - bill_view() shows working date in receipt header
  - owner_dashboard_ui() has date picker (independent of cashier work_date)
  - Dev Settings: menu editing (add/edit/delete), token hard cap field
  - Missing receipt check uses owner's selected dashboard date
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Callable

import pandas as pd
import streamlit as st


# ──────────────────────────────────────────────────────────────────────────────
# CSS
# ──────────────────────────────────────────────────────────────────────────────

def load_fancy_css() -> None:
    # Fonts loaded non-blocking via separate markdown call —
    # mixing <link> tags inside a <style> block causes Streamlit
    # to render the tags as visible text.
    st.markdown(
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
        '<link rel="stylesheet" media="print" onload="this.media=\'all\'" '
        'href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900'
        '&family=IBM+Plex+Mono:wght@400;600&family=DM+Sans:wght@300;400;500&display=swap">',
        unsafe_allow_html=True,
    )
    st.markdown(
        """<style>

        :root {
            --espresso:   #1a1007;
            --roast:      #2d1f0e;
            --mahogany:   #3d2b1a;
            --caramel:    #c07c3a;
            --gold:       #e0a84b;
            --cream:      #f5ead8;
            --steam:      #8a7566;
            --dev-dark:   #1e3a5f;
            --dev-accent: #4a90d9;
            --warn-bg:    #2a1f00;
            --warn-border:#c07c3a;
            --danger-bg:  #3d0a0a;
            --danger-bdr: #8b2e2e;
            --danger-txt: #e05555;
            --radius:     6px;
        }

        html, body, [data-testid="stAppViewContainer"] {
            background: var(--roast) !important;
            color: var(--cream) !important;
            font-family: 'DM Sans', system-ui, -apple-system, sans-serif !important;
        }
        [data-testid="stAppViewContainer"]::before {
            content:''; position:fixed; inset:0; pointer-events:none; z-index:0;
            background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='300' height='300'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3CfeColorMatrix type='saturate' values='0'/%3E%3C/filter%3E%3Crect width='300' height='300' filter='url(%23n)' opacity='0.04'/%3E%3C/svg%3E");
        }
        [data-testid="stAppViewBlockContainer"] { padding: 1rem 1.5rem !important; }

        [data-testid="stSidebar"] {
            background: var(--espresso) !important;
            border-right: 1px solid var(--mahogany) !important;
            min-width: 200px !important;
        }
        [data-testid="stSidebar"] * { color: var(--cream) !important; }

        .stButton > button {
            font-family: 'IBM Plex Mono', monospace !important;
            font-size: .75rem !important; font-weight: 600 !important;
            letter-spacing: .08em !important; text-transform: uppercase !important;
            background: var(--mahogany) !important; color: var(--gold) !important;
            border: 1px solid var(--caramel) !important;
            border-radius: var(--radius) !important;
            transition: all .15s ease !important;
            box-shadow: 0 2px 8px rgba(0,0,0,.4) !important;
            min-height: 2.4rem !important; padding: .45rem .8rem !important;
        }
        .stButton > button:hover {
            background: var(--caramel) !important; color: var(--espresso) !important;
            border-color: var(--gold) !important; transform: translateY(-1px) !important;
        }
        .stButton > button[kind="primary"] {
            background: var(--gold) !important; color: var(--espresso) !important;
            border-color: var(--gold) !important;
        }
        .stDownloadButton > button {
            font-family: 'IBM Plex Mono', monospace !important;
            font-size: .75rem !important; font-weight: 600 !important;
            background: var(--gold) !important; color: var(--espresso) !important;
            border: 1px solid var(--gold) !important;
            border-radius: var(--radius) !important; min-height: 2.4rem !important;
        }

        .stTextInput input, .stNumberInput input,
        .stSelectbox > div > div, .stMultiSelect > div > div,
        .stDateInput input {
            background: var(--espresso) !important; color: var(--cream) !important;
            border: 1px solid var(--mahogany) !important;
            border-radius: var(--radius) !important;
            font-family: 'DM Sans', sans-serif !important;
            font-size: 1rem !important;
        }
        .stTextInput input:focus, .stNumberInput input:focus,
        .stDateInput input:focus {
            border-color: var(--caramel) !important;
            box-shadow: 0 0 0 2px rgba(192,124,58,.2) !important;
        }
        .stCheckbox label { font-family: 'DM Sans', sans-serif !important; color: var(--cream) !important; }

        .stTabs [data-baseweb="tab-list"] {
            background: var(--espresso) !important;
            border-bottom: 2px solid var(--caramel) !important;
            gap: 0 !important; overflow-x: auto !important;
            -webkit-overflow-scrolling: touch !important; flex-wrap: nowrap !important;
        }
        .stTabs [data-baseweb="tab"] {
            font-family: 'IBM Plex Mono', monospace !important;
            font-size: .7rem !important; font-weight: 600 !important;
            letter-spacing: .08em !important; text-transform: uppercase !important;
            color: var(--steam) !important; padding: .6rem .9rem !important;
            white-space: nowrap !important; min-width: fit-content !important;
        }
        .stTabs [aria-selected="true"] {
            background: var(--mahogany) !important; color: var(--gold) !important;
            border-bottom: 2px solid var(--gold) !important;
        }

        [data-testid="stMetric"] {
            background: var(--espresso) !important;
            border: 1px solid var(--mahogany) !important;
            border-radius: var(--radius) !important; padding: .8rem !important;
        }
        [data-testid="stMetricLabel"] {
            font-family: 'IBM Plex Mono', monospace !important;
            font-size: .6rem !important; letter-spacing: .1em !important;
            text-transform: uppercase !important; color: var(--steam) !important;
        }
        [data-testid="stMetricValue"] {
            font-family: 'Playfair Display', serif !important;
            font-size: 1.6rem !important; color: var(--gold) !important;
        }

        .stAlert { border-radius: var(--radius) !important;
                   font-family: 'IBM Plex Mono', monospace !important;
                   font-size: .78rem !important; }

        [data-testid="stDataFrameContainer"] {
            overflow-x: auto !important; -webkit-overflow-scrolling: touch !important;
        }
        .streamlit-expanderHeader {
            background: var(--espresso) !important;
            border: 1px solid var(--mahogany) !important;
            border-radius: var(--radius) !important;
            font-family: 'DM Sans', sans-serif !important; color: var(--cream) !important;
        }
        .streamlit-expanderContent {
            background: var(--espresso) !important;
            border: 1px solid var(--mahogany) !important;
            border-top: none !important;
            border-radius: 0 0 var(--radius) var(--radius) !important;
        }

        hr { border-color: var(--mahogany) !important; margin: .8rem 0 !important; }
        ::-webkit-scrollbar { width: 5px; height: 5px; }
        ::-webkit-scrollbar-track { background: var(--espresso); }
        ::-webkit-scrollbar-thumb { background: var(--mahogany); border-radius: 3px; }
        ::-webkit-scrollbar-thumb:hover { background: var(--caramel); }

        /* Working date badge */
        .cb-date-badge {
            font-family: 'IBM Plex Mono', monospace;
            font-size: .68rem; font-weight: 600;
            letter-spacing: .1em; text-transform: uppercase;
            color: var(--gold); background: var(--mahogany);
            border: 1px solid var(--caramel);
            border-radius: var(--radius);
            padding: .3rem .7rem; display: inline-block;
        }
        .cb-date-badge.stale {
            color: #e09a3a; border-color: #c07c3a;
            background: var(--warn-bg);
        }

        @media (max-width: 640px) {
            [data-testid="stAppViewBlockContainer"] { padding: .6rem .7rem !important; }
            .stButton > button { min-height: 2.8rem !important; font-size: .8rem !important; }
            [data-testid="stHorizontalBlock"] { gap: .4rem !important; }
            [data-testid="stMetricValue"] { font-size: 1.3rem !important; }
            .stTabs [data-baseweb="tab"] { font-size: .65rem !important; padding: .5rem .6rem !important; }
            .cb-header-title { font-size: 1.4rem !important; }
        }
        @media (min-width: 641px) and (max-width: 1024px) {
            [data-testid="stAppViewBlockContainer"] { padding: .8rem 1rem !important; }
            [data-testid="stMetricValue"] { font-size: 1.5rem !important; }
            .cb-header-title { font-size: 1.6rem !important; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ──────────────────────────────────────────────────────────────────────────────
# HEADER / FOOTER
# ──────────────────────────────────────────────────────────────────────────────

def fancy_header(cafe_name: str = "CafeBoss",
                 tagline: str = "Modern Billing System") -> None:
    st.markdown(
        f"""<div style="display:flex;align-items:center;gap:12px;
                        padding:1rem 0 .6rem;border-bottom:2px solid #3d2b1a;
                        margin-bottom:1.2rem;flex-wrap:wrap;">
            <span style="font-size:2rem;line-height:1;">☕</span>
            <div>
                <div class="cb-header-title"
                     style="font-family:'Playfair Display',serif;font-size:1.9rem;
                            font-weight:900;color:#e0a84b;letter-spacing:-.01em;line-height:1;">
                    {cafe_name}</div>
                <div style="font-family:'IBM Plex Mono',monospace;font-size:.62rem;
                            color:#8a7566;letter-spacing:.16em;text-transform:uppercase;
                            margin-top:2px;">{tagline}</div>
            </div>
        </div>""",
        unsafe_allow_html=True,
    )


def fancy_footer(cafe_name: str = "CafeBoss") -> None:
    st.markdown(
        f"""<div style="margin-top:2.5rem;padding-top:.8rem;border-top:1px solid #3d2b1a;
                        font-family:'IBM Plex Mono',monospace;font-size:.58rem;color:#8a7566;
                        letter-spacing:.12em;text-align:center;text-transform:uppercase;">
            {cafe_name} &nbsp;·&nbsp; Billing System &nbsp;·&nbsp; All rights reserved
        </div>""",
        unsafe_allow_html=True,
    )


# ──────────────────────────────────────────────────────────────────────────────
# SETUP WIZARD
# ──────────────────────────────────────────────────────────────────────────────

def setup_wizard_ui(
    role: str,
    title: str,
    subtitle: str,
    on_save: Callable[[str], None],
) -> None:
    is_dev = role == "dev"
    accent = "#4a90d9" if is_dev else "#e0a84b"
    st.markdown(
        f"""<div style="max-width:440px;margin:3rem auto;text-align:center;padding:0 1rem;">
            <div style="font-family:'Playfair Display',serif;font-size:1.8rem;
                        color:{accent};margin-bottom:.4rem;">{title}</div>
            <div style="font-family:'IBM Plex Mono',monospace;font-size:.68rem;
                        color:#8a7566;letter-spacing:.14em;text-transform:uppercase;
                        margin-bottom:1.6rem;">{subtitle}</div>
            {"<div style='background:#1e3a5f;border:1px solid #2d5a8e;border-radius:6px;padding:.7rem 1rem;font-family:IBM Plex Mono,monospace;font-size:.66rem;color:#4a90d9;margin-bottom:1.2rem;text-align:left;'>⚠️ Keep this separate from the owner password.</div>" if is_dev else ""}
        </div>""",
        unsafe_allow_html=True,
    )
    with st.form(f"setup_{role}_form"):
        pw1 = st.text_input("New Password",     type="password", key=f"{role}_pw1")
        pw2 = st.text_input("Confirm Password", type="password", key=f"{role}_pw2")
        if st.form_submit_button(
            f"Set {'Developer' if is_dev else 'Owner'} Password",
            use_container_width=True,
        ):
            if not pw1:
                st.error("Password cannot be empty.")
            elif pw1 != pw2:
                st.error("Passwords do not match.")
            else:
                try:
                    on_save(pw1)
                    st.success("Password saved. Continuing…")
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))


# ──────────────────────────────────────────────────────────────────────────────
# ROLE LOGIN
# ──────────────────────────────────────────────────────────────────────────────

def role_login_ui(role: str, label: str) -> str | None:
    is_dev = role == "dev"
    border = "#2d5a8e" if is_dev else "#3d2b1a"
    color  = "#4a90d9" if is_dev else "#e0a84b"
    st.markdown(
        f"""<div style="background:#1a1007;border:1px solid {border};border-radius:8px;
                        padding:1.6rem;max-width:380px;margin:1.5rem auto;">
            <div style="font-family:'Playfair Display',serif;font-size:1.3rem;
                        color:{color};margin-bottom:1rem;text-align:center;">
                {label}</div>""",
        unsafe_allow_html=True,
    )
    with st.form(f"{role}_login_form"):
        password  = st.text_input("Password", type="password", key=f"{role}_pw_input")
        c1, c2    = st.columns(2)
        with c1:
            submitted = st.form_submit_button("Unlock", use_container_width=True)
        with c2:
            cancelled = st.form_submit_button("Cancel", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)
    if cancelled:
        return "cancel"
    if submitted and password:
        return password
    return None


# ──────────────────────────────────────────────────────────────────────────────
# WORKING DATE WIDGET  (sidebar)
# ──────────────────────────────────────────────────────────────────────────────

def working_date_ui(
    work_date: str,
    today: str,
    lookback_days: int,
    show_picker: bool,
    date_error: str | None,
    on_toggle_picker: Callable[[], None],
    on_change_date: Callable[[str], None],
) -> None:
    is_stale = work_date < today
    badge_class = "cb-date-badge stale" if is_stale else "cb-date-badge"
    label = f"{'⚠️ ' if is_stale else '📅 '}{work_date}"

    st.markdown(
        f"""<div style="margin-bottom:.4rem;">
            <div style="font-family:'IBM Plex Mono',monospace;font-size:.58rem;
                        color:#8a7566;letter-spacing:.12em;text-transform:uppercase;
                        margin-bottom:.3rem;">Working Date</div>
            <span class="{badge_class}">{label}</span>
        </div>""",
        unsafe_allow_html=True,
    )

    if st.button("Change Date", use_container_width=True, key="toggle_date_btn"):
        on_toggle_picker()

    if show_picker:
        earliest = (
            date.fromisoformat(today) - timedelta(days=lookback_days)
        ).isoformat()

        with st.form("date_change_form", clear_on_submit=False):
            selected = st.date_input(
                "Select working date",
                value=date.fromisoformat(work_date),
                min_value=date.fromisoformat(earliest),
                max_value=date.fromisoformat(today),
                key="date_picker_input",
            )
            if st.form_submit_button("✅ Confirm", use_container_width=True):
                on_change_date(selected.isoformat())

    if date_error:
        st.error(date_error)

    st.markdown("<hr>", unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────────────
# SIDEBAR: TOKEN BOARD + SAVE LOCATION
# ──────────────────────────────────────────────────────────────────────────────

def token_board(
    tokens: list[dict[str, Any]],
    selected_token_id: int | None,
    tokens_per_row: int,
    on_token_click: Callable[[int], None],
) -> None:
    _label_mono("Tokens")
    if not tokens:
        st.caption("No tokens. Configure in Owner Dashboard.")
        return
    cols_n = min(tokens_per_row, 3)
    rows   = [tokens[i : i + cols_n] for i in range(0, len(tokens), cols_n)]
    for row in rows:
        cols = st.columns(len(row))
        for col, token in zip(cols, row):
            with col:
                tid    = token["id"]
                active = bool(token["active"])
                is_sel = tid == selected_token_id
                label  = token.get("label", str(tid))
                icon   = "✅" if is_sel else ("🟠" if active else "⬜")
                if st.button(f"{icon}\n{tid}", key=f"tok_{tid}",
                             use_container_width=True, help=label):
                    on_token_click(tid)


def save_location_info(path: str, label: str) -> None:
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown(
        f"""<div style="font-family:'IBM Plex Mono',monospace;font-size:.6rem;
                        color:#8a7566;letter-spacing:.08em;line-height:1.6;">
            <div style="text-transform:uppercase;margin-bottom:2px;">Save Location</div>
            <div style="color:#c07c3a;">{label}</div>
            <div style="color:#4a3a2a;font-size:.54rem;word-break:break-all;
                        margin-top:2px;">{path}</div>
        </div>""",
        unsafe_allow_html=True,
    )
    st.markdown("<hr>", unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────────────
# BILL VIEW
# ──────────────────────────────────────────────────────────────────────────────

def bill_view(
    token: dict[str, Any],
    items: list[dict[str, Any]],
    currency: str,
    payment_methods: list[str],
    confirm_before_payment: bool,
    on_delete: Callable[[int], None],
    on_payment: Callable[[list[dict[str, Any]], float, str], None],
    confirm_state: bool,
    set_confirm: Callable[[bool], None],
    work_date: str,
    pending_download: dict[str, Any] | None = None,
) -> None:

    if pending_download:
        st.download_button(
            label=f"⬇️ Download Receipt — {pending_download['label']}",
            data=pending_download["csv"],
            file_name=pending_download["filename"],
            mime="text/csv",
            use_container_width=True,
            key=f"dl_{pending_download['bill_id'][:8]}",
        )
        st.markdown("<hr>", unsafe_allow_html=True)

    token_id    = token["id"]
    token_label = token.get("label", f"Token {token_id}")
    token_type  = token.get("type", "dine_in")
    type_badge  = {
        "dine_in":  "🪑 Dine-In",
        "takeaway": "🥡 Takeaway",
        "delivery": "🛵 Delivery",
        "online":   "💻 Online",
    }.get(token_type, token_type)

    st.markdown(
        f"""<div style="font-family:'IBM Plex Mono',monospace;background:#1a1007;
                        border:1px solid #3d2b1a;border-radius:6px 6px 0 0;
                        padding:.6rem 1rem;display:flex;justify-content:space-between;
                        align-items:center;flex-wrap:wrap;gap:.4rem;">
            <span style="font-size:.65rem;letter-spacing:.14em;text-transform:uppercase;
                          color:#8a7566;">
                Receipt &nbsp;·&nbsp;
                <span style="color:#c07c3a;">{work_date}</span>
            </span>
            <span style="font-size:.72rem;color:#e0a84b;font-weight:600;">
                {token_label}
                <span style="color:#8a7566;font-weight:400;"> · {type_badge}</span>
            </span>
        </div>""",
        unsafe_allow_html=True,
    )

    if not items:
        st.markdown(
            """<div style="background:#1a1007;border:1px solid #3d2b1a;border-top:none;
                           border-radius:0 0 6px 6px;padding:2rem;text-align:center;">
                <div style="font-size:1.8rem;margin-bottom:.4rem;">🍃</div>
                <div style="font-family:'IBM Plex Mono',monospace;font-size:.68rem;
                            color:#5a4a3a;letter-spacing:.1em;text-transform:uppercase;">
                    No items yet</div>
            </div>""",
            unsafe_allow_html=True,
        )
        return

    total = 0.0
    for item in items:
        line_id  = item["id"]
        name     = item.get("item_name", "?")
        qty      = item.get("quantity", 1)
        price    = item.get("unit_price", 0)
        subtotal = item.get("subtotal", 0)
        total   += subtotal

        ci, cd = st.columns([5, 1])
        with ci:
            st.markdown(
                f"""<div style="padding:.35rem 1rem;border-bottom:1px solid #2d1f0e;
                                font-family:'IBM Plex Mono',monospace;font-size:.72rem;">
                    <span style="color:#f5ead8;">{name}</span>
                    <span style="color:#5a4a3a;"> ×{qty}</span>
                    <span style="float:right;color:#e0a84b;">{currency}{subtotal:,.2f}</span>
                    <span style="float:right;color:#5a4a3a;margin-right:.8rem;">
                        @{currency}{price:,.2f}</span>
                </div>""",
                unsafe_allow_html=True,
            )
        with cd:
            if st.button("✕", key=f"del_{line_id}", help="Remove"):
                on_delete(line_id)

    total = round(total, 2)
    st.markdown(
        f"""<div style="background:#2d1f0e;border:1px solid #3d2b1a;border-top:none;
                        border-radius:0 0 6px 6px;padding:.7rem 1rem;
                        font-family:'IBM Plex Mono',monospace;
                        display:flex;justify-content:space-between;align-items:center;">
            <span style="font-size:.65rem;letter-spacing:.14em;text-transform:uppercase;
                          color:#8a7566;">Total</span>
            <span style="font-size:1.25rem;font-weight:700;color:#e0a84b;">
                {currency}{total:,.2f}</span>
        </div>""",
        unsafe_allow_html=True,
    )

    st.write("")
    method = st.selectbox("Payment Method", options=payment_methods,
                          key=f"pay_method_{token_id}")

    if not confirm_before_payment:
        if st.button("💳 Process Payment", use_container_width=True,
                     type="primary", key=f"pay_{token_id}"):
            on_payment(items, total, method)
    elif not confirm_state:
        if st.button("💳 Process Payment", use_container_width=True,
                     type="primary", key=f"pay_{token_id}"):
            set_confirm(True)
            st.rerun()
    else:
        st.warning(
            f"Confirm **{method.upper()}** payment of "
            f"**{currency}{total:,.2f}** for **{token_label}**?"
        )
        c1, c2 = st.columns(2)
        with c1:
            if st.button("✅ Confirm", use_container_width=True,
                         type="primary", key=f"conf_{token_id}"):
                set_confirm(False)
                on_payment(items, total, method)
        with c2:
            if st.button("❌ Cancel", use_container_width=True,
                         key=f"canc_{token_id}"):
                set_confirm(False)
                st.rerun()


# ──────────────────────────────────────────────────────────────────────────────
# ITEM SELECTOR
# ──────────────────────────────────────────────────────────────────────────────

def item_selector(
    menu_items: list[dict[str, Any]],
    token_id: int,
    currency: str,
    on_add: Callable[[dict[str, Any], int], None],
) -> None:
    _label_mono("Add Items")
    if not menu_items:
        st.info("No items available. Ask the developer to add items in Settings.")
        return
    categories = ["All"] + sorted({i.get("category", "—") for i in menu_items})
    sel_cat    = st.selectbox("Category", categories, key=f"cat_{token_id}")
    filtered   = (
        menu_items if sel_cat == "All"
        else [i for i in menu_items if i.get("category") == sel_cat]
    )
    if not filtered:
        st.caption("No items in this category.")
        return
    sel_name = st.selectbox("Item", [i["name"] for i in filtered],
                            key=f"item_{token_id}")
    sel_item = next(i for i in filtered if i["name"] == sel_name)
    price    = float(sel_item["price"])
    st.markdown(
        f"<div style='font-family:IBM Plex Mono,monospace;font-size:.78rem;"
        f"color:#c07c3a;margin:3px 0 6px;'>{currency}{price:,.2f}</div>",
        unsafe_allow_html=True,
    )
    qty = st.number_input("Qty", min_value=1, value=1, step=1,
                          key=f"qty_{token_id}")
    if st.button("＋ Add to Bill", use_container_width=True,
                 key=f"add_{token_id}"):
        on_add(sel_item, int(qty))


# ──────────────────────────────────────────────────────────────────────────────
# MENU VIEW
# ──────────────────────────────────────────────────────────────────────────────

def menu_view(
    menu_items: list[dict[str, Any]],
    currency: str,
    on_add: Callable[[str, float, str], None],
    on_update_price: Callable[[str, float], None],
    on_toggle_available: Callable[[str, bool], None],
    on_delete: Callable[[str], None],
) -> None:
    left, right = st.columns([3, 2])
    with left:
        _label_mono("Current Menu")
        if not menu_items:
            st.info("Menu is empty. Add your first item →")
        else:
            for item in menu_items:
                iid   = item["item_id"]
                avail = bool(item.get("available", 1))
                badge = "✅" if avail else "🔴"
                with st.expander(
                    f"{badge} **{item['name']}** — {currency}{item['price']:,.2f}"
                    f"  `{item.get('category','—')}`", expanded=False
                ):
                    new_price = st.number_input(
                        f"Price ({currency})", value=float(item["price"]),
                        min_value=0.01, key=f"ep_{iid}",
                    )
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        if st.button("💾 Save", key=f"sp_{iid}",
                                     use_container_width=True):
                            on_update_price(iid, new_price)
                    with c2:
                        if st.button(
                            "🔴 Disable" if avail else "✅ Enable",
                            key=f"av_{iid}", use_container_width=True,
                        ):
                            on_toggle_available(iid, not avail)
                    with c3:
                        if st.button("🗑 Del", key=f"delmenu_{iid}",
                                     use_container_width=True):
                            on_delete(iid)
    with right:
        _label_mono("Add New Item")
        with st.form("add_menu_item_form", clear_on_submit=True):
            name     = st.text_input("Item Name")
            price    = st.number_input(f"Price ({currency})", min_value=0.01,
                                       value=50.0, step=0.5)
            category = st.text_input("Category", value="Beverages")
            if st.form_submit_button("Add Item", use_container_width=True):
                try:
                    on_add(name.strip(), price, category.strip())
                    st.success(f"'{name}' added.")
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))


# ──────────────────────────────────────────────────────────────────────────────
# OWNER DASHBOARD
# ──────────────────────────────────────────────────────────────────────────────

def owner_dashboard_ui(
    total_bills: int,
    total_revenue: float,
    recent_bills: list[dict[str, Any]],
    missing_receipts: list[dict[str, Any]],
    all_tokens: list[dict[str, Any]],
    all_menu: list[dict[str, Any]],
    available_dates: list[str],
    dash_date: str,
    today: str,
    token_count: int,
    token_max: int,
    settings: dict[str, Any],
    settings_defaults: dict[str, Any],
    currency: str,
    token_types: list[str],
    dev_session_valid: bool,
    dev_session_timeout: int,
    on_logout: Callable[[], None],
    on_dash_date_change: Callable[[str], None],
    on_add_token: Callable[[str, str], None],
    on_toggle_token: Callable[[int, bool], None],
    on_rename_token: Callable[[int, str], None],
    on_menu_add: Callable[[str, float, str], None],
    on_menu_price: Callable[[str, float], None],
    on_menu_toggle: Callable[[str, bool], None],
    on_menu_delete: Callable[[str], None],
    on_save_settings: Callable[[dict[str, Any]], None],
    on_dev_login_attempt: Callable[[str], None],
    on_dev_logout: Callable[[], None],
    token_add_error: str | None = None,
    dev_login_error: bool = False,
) -> None:

    # ── Header ────────────────────────────────────────────────────────────────
    hc1, hc2 = st.columns([4, 1])
    with hc1:
        st.markdown(
            """<div style="font-family:'Playfair Display',serif;font-size:1.5rem;
                           color:#e0a84b;margin-bottom:.2rem;">👑 Owner Dashboard</div>""",
            unsafe_allow_html=True,
        )
    with hc2:
        if st.button("🔒 Logout", use_container_width=True):
            on_logout()

    # ── Date picker (owner-independent) ──────────────────────────────────────
    dc1, dc2 = st.columns([3, 1])
    with dc1:
        date_options = sorted(set(available_dates + [today]), reverse=True)
        sel_idx      = date_options.index(dash_date) if dash_date in date_options else 0
        chosen = st.selectbox(
            "Viewing date",
            options=date_options,
            index=sel_idx,
            key="dash_date_selector",
            format_func=lambda d: f"{'📅 Today' if d == today else '🗓 '+ d}",
        )
        if chosen != dash_date:
            on_dash_date_change(chosen)
    with dc2:
        st.markdown(
            f"<div style='font-family:IBM Plex Mono,monospace;font-size:.6rem;"
            f"color:#8a7566;text-transform:uppercase;letter-spacing:.1em;"
            f"padding-top:.4rem;'>System date<br>"
            f"<span style='color:#e0a84b;font-size:.75rem;'>{today}</span></div>",
            unsafe_allow_html=True,
        )

    st.markdown("<hr>", unsafe_allow_html=True)

    # ── KPIs ──────────────────────────────────────────────────────────────────
    n_missing = len(missing_receipts)
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Bills", total_bills)
    with m2:
        st.metric(f"Revenue ({currency})", f"{total_revenue:,.2f}")
    with m3:
        active_tok = sum(1 for t in all_tokens if t.get("active"))
        st.metric("Active Tokens", f"{active_tok}/{len(all_tokens)}")
    with m4:
        st.metric(
            "Missing Receipts", str(n_missing),
            delta="⚠️ deleted" if n_missing else "✅ intact",
            delta_color="inverse" if n_missing else "off",
        )

    if missing_receipts:
        st.markdown(
            f"""<div style="background:var(--danger-bg);border:1px solid var(--danger-bdr);
                            border-radius:6px;padding:.8rem 1rem;margin:.5rem 0;
                            font-family:'IBM Plex Mono',monospace;font-size:.72rem;">
                <span style="color:var(--danger-txt);font-weight:600;">
                    ⚠️ {n_missing} receipt file{"s" if n_missing > 1 else ""} missing
                    for {dash_date}
                </span><br>
                <span style="color:#c07070;font-size:.65rem;">
                    Transaction records are intact in the database.
                    Only the CSV export files are gone.
                </span>
            </div>""",
            unsafe_allow_html=True,
        )

    st.markdown("<hr>", unsafe_allow_html=True)

    dtab1, dtab2, dtab3 = st.tabs([
        "📊 Transactions", "🎫 Tokens", "⚙️ Settings"
    ])

    # ── Transactions ──────────────────────────────────────────────────────────
    with dtab1:
        if missing_receipts:
            _label_mono("⚠️ Missing Receipt Files")
            df_m = pd.DataFrame([{
                "Time":     r.get("paid_at", "")[-8:],
                "Token":    r.get("token_label", ""),
                "Amount":   f"{currency}{r.get('total', 0):,.2f}",
                "Method":   r.get("payment_method", "").upper(),
                "Filename": r.get("filename", ""),
            } for r in missing_receipts])
            st.dataframe(df_m, use_container_width=True, hide_index=True)
            st.caption(
                "These bills are fully recorded in the database. "
                "The CSV files on disk have been moved or deleted."
            )
            st.markdown("<hr>", unsafe_allow_html=True)

        if not recent_bills:
            st.info(f"No transactions recorded for {dash_date}.")
        else:
            df = pd.DataFrame(recent_bills)
            missing_ids = {r["id"] for r in missing_receipts}
            df["receipt"] = df["id"].apply(
                lambda bid: "⚠️ Missing" if bid in missing_ids else "✅ OK"
            )
            show = [c for c in ["paid_at", "work_date", "token_label",
                                  "token_type", "total", "payment_method",
                                  "receipt", "id"]
                    if c in df.columns]
            st.dataframe(df[show], use_container_width=True, hide_index=True)

    # ── Tokens ────────────────────────────────────────────────────────────────
    with dtab2:
        # Token cap indicator
        cap_pct = int(token_count / token_max * 100) if token_max else 100
        st.markdown(
            f"""<div style="background:#1a1007;border:1px solid #3d2b1a;
                            border-radius:6px;padding:.6rem 1rem;margin-bottom:.8rem;
                            font-family:'IBM Plex Mono',monospace;font-size:.68rem;">
                <span style="color:#8a7566;text-transform:uppercase;
                              letter-spacing:.1em;">Token Usage &nbsp;</span>
                <span style="color:#e0a84b;font-weight:600;">
                    {token_count} / {token_max}</span>
                {"&nbsp;<span style='color:#e05555;'>— cap reached</span>" if token_count >= token_max else ""}
            </div>""",
            unsafe_allow_html=True,
        )

        if token_add_error:
            st.error(token_add_error)

        _label_mono("All Tokens")
        for token in all_tokens:
            tid     = token["id"]
            enabled = bool(token.get("enabled", 1))
            active  = bool(token.get("active",  0))
            label   = token.get("label", f"Token {tid}")
            ttype   = token.get("type",  "dine_in")
            status  = "🟠 Active" if active else ("✅ Idle" if enabled else "⛔ Disabled")
            with st.expander(
                f"**{label}** — {status}  `{ttype}`", expanded=False
            ):
                new_label = st.text_input("Rename", value=label, key=f"ren_{tid}")
                rc1, rc2, rc3 = st.columns(3)
                with rc1:
                    if st.button("💾 Save", key=f"rsv_{tid}",
                                 use_container_width=True):
                        on_rename_token(tid, new_label.strip())
                with rc2:
                    if st.button(
                        "⛔ Disable" if enabled else "✅ Enable",
                        key=f"tog_{tid}", use_container_width=True,
                    ):
                        on_toggle_token(tid, not enabled)
                with rc3:
                    st.caption(f"Since: {token.get('opened_at','—')}")

        if token_count < token_max:
            st.markdown("<hr>", unsafe_allow_html=True)
            _label_mono("Add New Token")
            with st.form("add_token_form", clear_on_submit=True):
                nl = st.text_input("Label", placeholder="e.g. Drive-Through 1")
                nt = st.selectbox("Type", token_types, key="new_tok_type")
                if st.form_submit_button("Add Token", use_container_width=True):
                    if nl.strip():
                        on_add_token(nl.strip(), nt)
                    else:
                        st.error("Label cannot be empty.")
        else:
            st.info(
                f"Token cap of {token_max} reached. "
                "Ask the developer to raise the limit in Settings."
            )

    # ── Settings (dev locked) ─────────────────────────────────────────────────
    with dtab3:
        _settings_tab(
            settings=settings,
            all_menu=all_menu,
            currency=currency,
            token_count=token_count,
            token_max=token_max,
            dev_session_valid=dev_session_valid,
            dev_session_timeout=dev_session_timeout,
            on_save_settings=on_save_settings,
            on_menu_add=on_menu_add,
            on_menu_price=on_menu_price,
            on_menu_toggle=on_menu_toggle,
            on_menu_delete=on_menu_delete,
            on_dev_login_attempt=on_dev_login_attempt,
            on_dev_logout=on_dev_logout,
            dev_login_error=dev_login_error,
        )


# ──────────────────────────────────────────────────────────────────────────────
# SETTINGS TAB
# ──────────────────────────────────────────────────────────────────────────────

def _settings_tab(
    settings: dict[str, Any],
    all_menu: list[dict[str, Any]],
    currency: str,
    token_count: int,
    token_max: int,
    dev_session_valid: bool,
    dev_session_timeout: int,
    on_save_settings: Callable[[dict[str, Any]], None],
    on_menu_add: Callable[[str, float, str], None],
    on_menu_price: Callable[[str, float], None],
    on_menu_toggle: Callable[[str, bool], None],
    on_menu_delete: Callable[[str], None],
    on_dev_login_attempt: Callable[[str], None],
    on_dev_logout: Callable[[], None],
    dev_login_error: bool,
) -> None:

    if not dev_session_valid:
        st.markdown(
            """<div style="background:#1e3a5f;border:1px solid #2d5a8e;border-radius:8px;
                           padding:1.4rem;max-width:400px;margin:1rem auto 1.5rem;">
                <div style="font-family:'Playfair Display',serif;font-size:1.1rem;
                            color:#4a90d9;margin-bottom:.3rem;text-align:center;">
                    🔧 Developer Access Required</div>
                <div style="font-family:'IBM Plex Mono',monospace;font-size:.6rem;
                            color:#8aabcc;letter-spacing:.1em;text-transform:uppercase;
                            text-align:center;margin-bottom:1rem;">
                    System settings are protected</div>""",
            unsafe_allow_html=True,
        )
        if dev_login_error:
            st.error("Invalid developer password.")
        with st.form("dev_unlock_form"):
            pw = st.text_input("Developer Password", type="password",
                               key="dev_unlock_pw")
            if st.form_submit_button("🔓 Unlock Settings",
                                     use_container_width=True):
                if pw:
                    on_dev_login_attempt(pw)
                else:
                    st.error("Password cannot be empty.")
        st.markdown("</div>", unsafe_allow_html=True)
        # Blurred preview
        st.markdown(
            "<div style='opacity:.3;pointer-events:none;filter:blur(2px);margin-top:.8rem;'>",
            unsafe_allow_html=True,
        )
        st.text_input("Café Name",       value="••••••••", disabled=True, key="_pn")
        st.text_input("Currency Symbol", value="•",        disabled=True, key="_pc")
        st.number_input("Token Cap",     value=50,         disabled=True, key="_pk")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    # ── Dev session status bar ────────────────────────────────────────────────
    sc1, sc2 = st.columns([4, 1])
    with sc1:
        note = (f"Session expires in {dev_session_timeout} min"
                if dev_session_timeout > 0 else "Session never expires")
        st.markdown(
            f"""<div style="background:#1e3a5f;border:1px solid #2d5a8e;
                            border-radius:6px;padding:.55rem 1rem;
                            font-family:'IBM Plex Mono',monospace;
                            font-size:.65rem;color:#4a90d9;">
                🔧 Developer session active &nbsp;·&nbsp;
                <span style="color:#8aabcc;">{note}</span></div>""",
            unsafe_allow_html=True,
        )
    with sc2:
        if st.button("🔒 Dev Logout", use_container_width=True,
                     key="dev_logout_btn"):
            on_dev_logout()
    st.write("")

    # ── Settings tabs inside Settings (keep things organised) ─────────────────
    st1, st2, st3 = st.tabs(["🏪 General", "📋 Menu", "🎫 Token Cap"])

    # ── General settings form ──────────────────────────────────────────────────
    with st1:
        _label_mono("System Settings")
        st.caption("Changes apply immediately and persist across restarts.")
        with st.form("settings_form"):
            upd: dict[str, Any] = {}

            _section("Identity")
            upd["cafe_name"]       = st.text_input("Café Name",
                value=settings.get("cafe_name", "CafeBoss"))
            upd["cafe_tagline"]    = st.text_input("Tagline",
                value=settings.get("cafe_tagline", ""))
            upd["currency_symbol"] = st.text_input("Currency Symbol",
                value=settings.get("currency_symbol", "₹"))

            st.markdown("<hr>", unsafe_allow_html=True)
            _section("Security & Sessions")
            upd["password_expiry_days"] = st.number_input(
                "Password Expiry (days, 0 = never)", min_value=0,
                value=int(settings.get("password_expiry_days", 30)),
            )
            upd["owner_session_timeout_mins"] = st.number_input(
                "Owner Session Timeout (mins, 0 = never)", min_value=0,
                value=int(settings.get("owner_session_timeout_mins", 60)),
            )
            upd["dev_session_timeout_mins"] = st.number_input(
                "Developer Session Timeout (mins, 0 = never)", min_value=0,
                value=int(settings.get("dev_session_timeout_mins", 30)),
            )

            st.markdown("<hr>", unsafe_allow_html=True)
            _section("Working Date")
            upd["work_date_lookback_days"] = st.number_input(
                "Max days back cashier can set working date",
                min_value=1, max_value=30,
                value=int(settings.get("work_date_lookback_days", 3)),
            )

            st.markdown("<hr>", unsafe_allow_html=True)
            _section("Payments")
            upd["payment_methods"] = st.multiselect(
                "Accepted Payment Methods",
                options=["cash", "card", "upi", "online"],
                default=settings.get("payment_methods",
                                      ["cash", "card", "upi", "online"]),
            )

            st.markdown("<hr>", unsafe_allow_html=True)
            _section("Behaviour")
            upd["confirm_before_payment"] = st.checkbox(
                "Require payment confirmation step",
                value=bool(settings.get("confirm_before_payment", True)),
            )
            upd["save_csv_receipt"] = st.checkbox(
                "Save CSV receipt to disk on payment",
                value=bool(settings.get("save_csv_receipt", True)),
            )

            if st.form_submit_button("💾 Save Settings",
                                     use_container_width=True, type="primary"):
                on_save_settings(upd)

    # ── Menu editing (dev only) ────────────────────────────────────────────────
    with st2:
        left, right = st.columns([3, 2])
        with left:
            _label_mono("Current Menu")
            if not all_menu:
                st.info("Menu is empty. Add your first item →")
            else:
                for item in all_menu:
                    iid   = item["item_id"]
                    avail = bool(item.get("available", 1))
                    badge = "✅" if avail else "🔴"
                    with st.expander(
                        f"{badge} **{item['name']}** — {currency}{item['price']:,.2f}"
                        f"  `{item.get('category','—')}`", expanded=False
                    ):
                        new_price = st.number_input(
                            f"Price ({currency})", value=float(item["price"]),
                            min_value=0.01, key=f"ep_{iid}",
                        )
                        c1, c2, c3 = st.columns(3)
                        with c1:
                            if st.button("💾 Save", key=f"sp_{iid}",
                                         use_container_width=True):
                                on_menu_price(iid, new_price)
                        with c2:
                            if st.button(
                                "🔴 Disable" if avail else "✅ Enable",
                                key=f"av_{iid}", use_container_width=True,
                            ):
                                on_menu_toggle(iid, not avail)
                        with c3:
                            if st.button("🗑 Del", key=f"delmenu_{iid}",
                                         use_container_width=True):
                                on_menu_delete(iid)
        with right:
            _label_mono("Add New Item")
            with st.form("add_menu_item_form", clear_on_submit=True):
                name     = st.text_input("Item Name")
                price    = st.number_input(f"Price ({currency})", min_value=0.01,
                                           value=50.0, step=0.5)
                category = st.text_input("Category", value="Beverages")
                if st.form_submit_button("Add Item", use_container_width=True):
                    if name.strip():
                        try:
                            on_menu_add(name.strip(), price, category.strip())
                        except ValueError as exc:
                            st.error(str(exc))
                    else:
                        st.error("Name cannot be empty.")

    # ── Token cap ──────────────────────────────────────────────────────────────
    with st3:
        _label_mono("Token Hard Cap")
        st.caption(
            "The owner cannot add tokens beyond this number. "
            "Lowering it below the current token count has no effect on existing tokens."
        )

        used_pct = int(token_count / token_max * 100) if token_max else 100
        st.markdown(
            f"""<div style="background:#1a1007;border:1px solid #3d2b1a;
                            border-radius:6px;padding:.8rem 1rem;margin-bottom:1rem;
                            font-family:'IBM Plex Mono',monospace;font-size:.72rem;">
                <div style="color:#8a7566;text-transform:uppercase;
                              letter-spacing:.1em;font-size:.6rem;margin-bottom:.3rem;">
                    Current usage</div>
                <span style="color:#e0a84b;font-size:1.1rem;font-weight:700;">
                    {token_count}</span>
                <span style="color:#8a7566;"> / {token_max} tokens</span>
                <span style="color:{'#e05555' if used_pct >= 100 else '#8a7566'};">
                    &nbsp;({used_pct}%)</span>
            </div>""",
            unsafe_allow_html=True,
        )

        with st.form("token_cap_form"):
            new_max = st.number_input(
                "Token Cap",
                min_value=max(1, token_count),   # can't set below current count
                max_value=500,
                value=token_max,
                help=f"Current token count is {token_count}. Cap cannot go below that.",
            )
            if st.form_submit_button("💾 Save Token Cap",
                                     use_container_width=True, type="primary"):
                on_save_settings({"token_max": int(new_max)})


# ──────────────────────────────────────────────────────────────────────────────
# INTERNAL HELPERS
# ──────────────────────────────────────────────────────────────────────────────

def _label_mono(text: str) -> None:
    st.markdown(
        f"<div style='font-family:IBM Plex Mono,monospace;font-size:.6rem;"
        f"color:#8a7566;letter-spacing:.16em;text-transform:uppercase;"
        f"margin-bottom:.5rem;'>{text}</div>",
        unsafe_allow_html=True,
    )


def _section(text: str) -> None:
    st.markdown(
        f"<div style='font-family:IBM Plex Mono,monospace;font-size:.62rem;"
        f"color:#8a7566;letter-spacing:.1em;text-transform:uppercase;"
        f"margin:.6rem 0 .3rem;'>{text}</div>",
        unsafe_allow_html=True,
    )
