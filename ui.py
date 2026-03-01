"""
ui.py — CafeBoss UI Layer
Pure rendering — no DB calls, no business logic.
Responsive for desktop, tablet (768px+), and mobile (<768px).
"""

from __future__ import annotations

from typing import Any, Callable

import pandas as pd
import streamlit as st


# ──────────────────────────────────────────────────────────────────────────────
# CSS  — desktop + tablet + mobile
# ──────────────────────────────────────────────────────────────────────────────

def load_fancy_css() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=IBM+Plex+Mono:wght@400;600&family=DM+Sans:wght@300;400;500&display=swap');

        /* ── PALETTE ─────────────────────────────────────────────────────── */
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
            --danger-bg:  #3d0a0a;
            --danger-border: #8b2e2e;
            --danger-text:   #e05555;
            --radius:     6px;
        }

        /* ── BASE ────────────────────────────────────────────────────────── */
        html, body, [data-testid="stAppViewContainer"] {
            background: var(--roast) !important;
            color: var(--cream) !important;
            font-family: 'DM Sans', sans-serif !important;
        }
        /* Noise texture */
        [data-testid="stAppViewContainer"]::before {
            content:''; position:fixed; inset:0; pointer-events:none; z-index:0;
            background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='300' height='300'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3CfeColorMatrix type='saturate' values='0'/%3E%3C/filter%3E%3Crect width='300' height='300' filter='url(%23n)' opacity='0.04'/%3E%3C/svg%3E");
        }
        /* Main content area padding — more compact on small screens */
        [data-testid="stAppViewBlockContainer"] {
            padding: 1rem 1.5rem !important;
        }

        /* ── SIDEBAR ─────────────────────────────────────────────────────── */
        [data-testid="stSidebar"] {
            background: var(--espresso) !important;
            border-right: 1px solid var(--mahogany) !important;
            min-width: 200px !important;
        }
        [data-testid="stSidebar"] * { color: var(--cream) !important; }
        /* Collapse sidebar button area */
        [data-testid="stSidebarCollapseButton"] {
            background: var(--mahogany) !important;
        }

        /* ── BUTTONS ─────────────────────────────────────────────────────── */
        .stButton > button {
            font-family: 'IBM Plex Mono', monospace !important;
            font-size: .75rem !important;
            font-weight: 600 !important;
            letter-spacing: .08em !important;
            text-transform: uppercase !important;
            background: var(--mahogany) !important;
            color: var(--gold) !important;
            border: 1px solid var(--caramel) !important;
            border-radius: var(--radius) !important;
            transition: all .15s ease !important;
            box-shadow: 0 2px 8px rgba(0,0,0,.4) !important;
            /* Mobile: full-width feel, easy tap target */
            min-height: 2.4rem !important;
            padding: .45rem .8rem !important;
        }
        .stButton > button:hover {
            background: var(--caramel) !important;
            color: var(--espresso) !important;
            border-color: var(--gold) !important;
            transform: translateY(-1px) !important;
        }
        .stButton > button:active {
            transform: translateY(0) !important;
        }
        .stButton > button[kind="primary"] {
            background: var(--gold) !important;
            color: var(--espresso) !important;
            border-color: var(--gold) !important;
        }
        /* Download button matches style */
        .stDownloadButton > button {
            font-family: 'IBM Plex Mono', monospace !important;
            font-size: .75rem !important;
            font-weight: 600 !important;
            letter-spacing: .08em !important;
            text-transform: uppercase !important;
            background: var(--gold) !important;
            color: var(--espresso) !important;
            border: 1px solid var(--gold) !important;
            border-radius: var(--radius) !important;
            min-height: 2.4rem !important;
        }

        /* ── INPUTS ──────────────────────────────────────────────────────── */
        .stTextInput input,
        .stNumberInput input,
        .stSelectbox > div > div,
        .stMultiSelect > div > div {
            background: var(--espresso) !important;
            color: var(--cream) !important;
            border: 1px solid var(--mahogany) !important;
            border-radius: var(--radius) !important;
            font-family: 'DM Sans', sans-serif !important;
            /* Prevent iOS zoom on focus (needs font-size >= 16px equivalent) */
            font-size: 1rem !important;
        }
        .stTextInput input:focus,
        .stNumberInput input:focus {
            border-color: var(--caramel) !important;
            box-shadow: 0 0 0 2px rgba(192,124,58,.2) !important;
            outline: none !important;
        }
        /* Checkbox */
        .stCheckbox label {
            font-family: 'DM Sans', sans-serif !important;
            color: var(--cream) !important;
        }

        /* ── TABS ────────────────────────────────────────────────────────── */
        .stTabs [data-baseweb="tab-list"] {
            background: var(--espresso) !important;
            border-bottom: 2px solid var(--caramel) !important;
            gap: 0 !important;
            overflow-x: auto !important;      /* scroll on narrow screens */
            -webkit-overflow-scrolling: touch !important;
            flex-wrap: nowrap !important;
        }
        .stTabs [data-baseweb="tab"] {
            font-family: 'IBM Plex Mono', monospace !important;
            font-size: .7rem !important;
            font-weight: 600 !important;
            letter-spacing: .08em !important;
            text-transform: uppercase !important;
            color: var(--steam) !important;
            padding: .6rem .9rem !important;
            white-space: nowrap !important;
            min-width: fit-content !important;
        }
        .stTabs [aria-selected="true"] {
            background: var(--mahogany) !important;
            color: var(--gold) !important;
            border-bottom: 2px solid var(--gold) !important;
        }

        /* ── METRICS ─────────────────────────────────────────────────────── */
        [data-testid="stMetric"] {
            background: var(--espresso) !important;
            border: 1px solid var(--mahogany) !important;
            border-radius: var(--radius) !important;
            padding: .8rem !important;
        }
        [data-testid="stMetricLabel"] {
            font-family: 'IBM Plex Mono', monospace !important;
            font-size: .6rem !important;
            letter-spacing: .1em !important;
            text-transform: uppercase !important;
            color: var(--steam) !important;
        }
        [data-testid="stMetricValue"] {
            font-family: 'Playfair Display', serif !important;
            font-size: 1.6rem !important;
            color: var(--gold) !important;
        }

        /* ── ALERTS ──────────────────────────────────────────────────────── */
        .stAlert {
            border-radius: var(--radius) !important;
            font-family: 'IBM Plex Mono', monospace !important;
            font-size: .78rem !important;
        }

        /* ── DATAFRAME ───────────────────────────────────────────────────── */
        [data-testid="stDataFrameContainer"] {
            overflow-x: auto !important;
            -webkit-overflow-scrolling: touch !important;
        }

        /* ── EXPANDER ────────────────────────────────────────────────────── */
        .streamlit-expanderHeader {
            background: var(--espresso) !important;
            border: 1px solid var(--mahogany) !important;
            border-radius: var(--radius) !important;
            font-family: 'DM Sans', sans-serif !important;
            color: var(--cream) !important;
        }
        .streamlit-expanderContent {
            background: var(--espresso) !important;
            border: 1px solid var(--mahogany) !important;
            border-top: none !important;
            border-radius: 0 0 var(--radius) var(--radius) !important;
        }

        /* ── DIVIDER ─────────────────────────────────────────────────────── */
        hr { border-color: var(--mahogany) !important; margin: .8rem 0 !important; }

        /* ── SCROLLBAR ───────────────────────────────────────────────────── */
        ::-webkit-scrollbar { width: 5px; height: 5px; }
        ::-webkit-scrollbar-track { background: var(--espresso); }
        ::-webkit-scrollbar-thumb { background: var(--mahogany); border-radius: 3px; }
        ::-webkit-scrollbar-thumb:hover { background: var(--caramel); }

        /* ── MOBILE  (<640px) ────────────────────────────────────────────── */
        @media (max-width: 640px) {
            /* Tighter padding */
            [data-testid="stAppViewBlockContainer"] {
                padding: .6rem .7rem !important;
            }
            /* Larger tap targets on buttons */
            .stButton > button {
                min-height: 2.8rem !important;
                font-size: .8rem !important;
            }
            /* Stack columns vertically — Streamlit columns don't auto-stack,
               but we shrink gaps so narrower screens are usable */
            [data-testid="stHorizontalBlock"] {
                gap: .4rem !important;
            }
            /* Metric values slightly smaller */
            [data-testid="stMetricValue"] {
                font-size: 1.3rem !important;
            }
            /* Tab text */
            .stTabs [data-baseweb="tab"] {
                font-size: .65rem !important;
                padding: .5rem .6rem !important;
            }
            /* Header title */
            .cb-header-title {
                font-size: 1.4rem !important;
            }
        }

        /* ── TABLET (641px–1024px) ───────────────────────────────────────── */
        @media (min-width: 641px) and (max-width: 1024px) {
            [data-testid="stAppViewBlockContainer"] {
                padding: .8rem 1rem !important;
            }
            [data-testid="stMetricValue"] {
                font-size: 1.5rem !important;
            }
            .cb-header-title {
                font-size: 1.6rem !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ──────────────────────────────────────────────────────────────────────────────
# HEADER / FOOTER
# ──────────────────────────────────────────────────────────────────────────────

def fancy_header(cafe_name: str = "CafeBoss", tagline: str = "Modern Billing System") -> None:
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
                            margin-top:2px;">
                    {tagline}</div>
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
# SETUP WIZARD  (first-run, owner then dev)
# ──────────────────────────────────────────────────────────────────────────────

def setup_wizard_ui(
    role: str,
    title: str,
    subtitle: str,
    on_save: Callable[[str], None],
) -> None:
    is_dev  = role == "dev"
    accent  = "#4a90d9" if is_dev else "#e0a84b"

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
# ROLE LOGIN  (generic — owner or dev)
# Returns: password string | "cancel" | None
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
# SIDEBAR COMPONENTS
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

    # On very narrow sidebar clamp columns to 3
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
                if st.button(
                    f"{icon}\n{tid}",
                    key=f"tok_{tid}",
                    use_container_width=True,
                    help=label,
                ):
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
    pending_download: dict[str, Any] | None = None,
) -> None:

    # Windows download button — render FIRST so it survives rerun
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

    # Receipt header
    st.markdown(
        f"""<div style="font-family:'IBM Plex Mono',monospace;background:#1a1007;
                        border:1px solid #3d2b1a;border-radius:6px 6px 0 0;
                        padding:.6rem 1rem;display:flex;justify-content:space-between;
                        align-items:center;flex-wrap:wrap;gap:.4rem;">
            <span style="font-size:.65rem;letter-spacing:.14em;text-transform:uppercase;
                          color:#8a7566;">Receipt</span>
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

    # Line items
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

    # Total bar
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
    method = st.selectbox(
        "Payment Method", options=payment_methods,
        key=f"pay_method_{token_id}",
    )

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
        st.info("No items available. Add them in the Menu tab.")
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

    sel_name = st.selectbox("Item", [i["name"] for i in filtered], key=f"item_{token_id}")
    sel_item = next(i for i in filtered if i["name"] == sel_name)
    price    = float(sel_item["price"])

    st.markdown(
        f"<div style='font-family:IBM Plex Mono,monospace;font-size:.78rem;"
        f"color:#c07c3a;margin:3px 0 6px;'>{currency}{price:,.2f}</div>",
        unsafe_allow_html=True,
    )
    qty = st.number_input("Qty", min_value=1, value=1, step=1, key=f"qty_{token_id}")
    if st.button("＋ Add to Bill", use_container_width=True, key=f"add_{token_id}"):
        on_add(sel_item, int(qty))


# ──────────────────────────────────────────────────────────────────────────────
# MENU VIEW  (cashier + owner)
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
                    f"  `{item.get('category','—')}`",
                    expanded=False,
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
    settings: dict[str, Any],
    settings_defaults: dict[str, Any],
    currency: str,
    token_types: list[str],
    dev_session_valid: bool,
    dev_session_timeout: int,
    on_logout: Callable[[], None],
    on_add_token: Callable[[str, str], None],
    on_toggle_token: Callable[[int, bool], None],
    on_rename_token: Callable[[int, str], None],
    on_menu_add: Callable[[str, float, str, float], None],
    on_menu_price: Callable[[str, float], None],
    on_menu_toggle: Callable[[str, bool], None],
    on_menu_delete: Callable[[str], None],
    on_save_settings: Callable[[dict[str, Any]], None],
    on_dev_login_attempt: Callable[[str], None],
    on_dev_logout: Callable[[], None],
    dev_login_error: bool = False,
) -> None:

    # ── Header ────────────────────────────────────────────────────────────────
    hc1, hc2 = st.columns([4, 1])
    with hc1:
        st.markdown(
            """<div style="font-family:'Playfair Display',serif;font-size:1.5rem;
                           color:#e0a84b;margin-bottom:.2rem;">👑 Owner Dashboard</div>
               <div style="font-family:'IBM Plex Mono',monospace;font-size:.6rem;
                           color:#8a7566;letter-spacing:.14em;text-transform:uppercase;">
                   Today's summary</div>""",
            unsafe_allow_html=True,
        )
    with hc2:
        if st.button("🔒 Logout", use_container_width=True):
            on_logout()

    st.markdown("<hr>", unsafe_allow_html=True)

    # ── KPIs — responsive: 2 cols on mobile, 4 on desktop ────────────────────
    n_missing = len(missing_receipts)
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Bills Today", total_bills)
    with m2:
        st.metric(f"Revenue ({currency})", f"{total_revenue:,.2f}")
    with m3:
        active_tok = sum(1 for t in all_tokens if t.get("active"))
        st.metric("Active Tokens", f"{active_tok}/{len(all_tokens)}")
    with m4:
        st.metric(
            "Missing Receipts",
            str(n_missing),
            delta="⚠️ deleted" if n_missing else "✅ intact",
            delta_color="inverse" if n_missing else "off",
        )

    # File integrity banner
    if missing_receipts:
        st.markdown(
            f"""<div style="background:var(--danger-bg);border:1px solid var(--danger-border);
                            border-radius:6px;padding:.8rem 1rem;margin:.5rem 0;
                            font-family:'IBM Plex Mono',monospace;font-size:.72rem;">
                <span style="color:var(--danger-text);font-weight:600;">
                    ⚠️ {n_missing} receipt file{"s" if n_missing > 1 else ""} missing from disk
                </span><br>
                <span style="color:#c07070;font-size:.65rem;">
                    Transaction records are intact in the database.
                    Only the CSV export files are gone.
                </span>
            </div>""",
            unsafe_allow_html=True,
        )

    st.markdown("<hr>", unsafe_allow_html=True)

    # ── Dashboard tabs ────────────────────────────────────────────────────────
    dtab1, dtab2, dtab3, dtab4 = st.tabs([
        "📊 Transactions", "🎫 Tokens", "📋 Menu", "⚙️ Settings"
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
            st.info("No transactions recorded today.")
        else:
            df = pd.DataFrame(recent_bills)
            missing_ids = {r["id"] for r in missing_receipts}
            df["receipt"] = df["id"].apply(
                lambda bid: "⚠️ Missing" if bid in missing_ids else "✅ OK"
            )
            show = [c for c in ["paid_at", "token_label", "token_type",
                                  "total", "payment_method", "receipt", "id"]
                    if c in df.columns]
            st.dataframe(df[show], use_container_width=True, hide_index=True)

    # ── Tokens ────────────────────────────────────────────────────────────────
    with dtab2:
        _label_mono("All Tokens")
        for token in all_tokens:
            tid     = token["id"]
            enabled = bool(token.get("enabled", 1))
            active  = bool(token.get("active",  0))
            label   = token.get("label", f"Token {tid}")
            ttype   = token.get("type",  "dine_in")
            status  = "🟠 Active" if active else ("✅ Idle" if enabled else "⛔ Disabled")

            with st.expander(f"**{label}** — {status}  `{ttype}`", expanded=False):
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

    # ── Menu ──────────────────────────────────────────────────────────────────
    with dtab3:
        menu_view(
            menu_items=all_menu,
            currency=currency,
            on_add=lambda n, p, c: on_menu_add(n, p, c, 0.0),
            on_update_price=on_menu_price,
            on_toggle_available=on_menu_toggle,
            on_delete=on_menu_delete,
        )

    # ── Settings — dev locked ─────────────────────────────────────────────────
    with dtab4:
        _settings_tab(
            settings=settings,
            currency=currency,
            dev_session_valid=dev_session_valid,
            dev_session_timeout=dev_session_timeout,
            on_save_settings=on_save_settings,
            on_dev_login_attempt=on_dev_login_attempt,
            on_dev_logout=on_dev_logout,
            dev_login_error=dev_login_error,
        )


# ──────────────────────────────────────────────────────────────────────────────
# SETTINGS TAB  (dev-gated)
# ──────────────────────────────────────────────────────────────────────────────

def _settings_tab(
    settings: dict[str, Any],
    currency: str,
    dev_session_valid: bool,
    dev_session_timeout: int,
    on_save_settings: Callable[[dict[str, Any]], None],
    on_dev_login_attempt: Callable[[str], None],
    on_dev_logout: Callable[[], None],
    dev_login_error: bool,
) -> None:

    if dev_session_valid:
        # Status bar
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

        # ── Settings form ─────────────────────────────────────────────────────
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
            _section("Tokens")
            upd["token_count"] = st.number_input(
                "Token Count (bootstrap min)", min_value=1, max_value=200,
                value=int(settings.get("token_count", 10)),
                help="Adds tokens up to this number on startup. Never removes existing.",
            )
            upd["token_label_prefix"] = st.text_input(
                "Token Label Prefix",
                value=settings.get("token_label_prefix", "Token"),
                help="e.g. 'Table' → Table 1, Table 2 …",
            )
            upd["tokens_per_row"] = st.number_input(
                "Tokens Per Row (sidebar)", min_value=1, max_value=10,
                value=int(settings.get("tokens_per_row", 5)),
            )

            st.markdown("<hr>", unsafe_allow_html=True)
            _section("Tax & Payments")
            upd["default_tax_rate"] = st.number_input(
                "Default Tax Rate (%)", min_value=0.0, max_value=100.0,
                value=float(settings.get("default_tax_rate", 0.0)),
            )
            upd["payment_methods"] = st.multiselect(
                "Accepted Payment Methods",
                options=["cash", "card", "upi", "online"],
                default=settings.get("payment_methods",
                                      ["cash", "card", "upi", "online"]),
            )

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

    else:
        # ── Dev login prompt ──────────────────────────────────────────────────
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
            "<div style='opacity:.3;pointer-events:none;filter:blur(2px);"
            "margin-top:.8rem;'>",
            unsafe_allow_html=True,
        )
        st.text_input("Café Name",       value="••••••••", disabled=True, key="_pn")
        st.text_input("Currency Symbol", value="•",        disabled=True, key="_pc")
        st.number_input("Tax Rate (%)",  value=0.0,        disabled=True, key="_pt")
        st.number_input("Token Count",   value=10,         disabled=True, key="_pk")
        st.markdown("</div>", unsafe_allow_html=True)


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
