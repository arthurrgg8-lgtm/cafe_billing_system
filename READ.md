# ☕ CafeBoss — Modern Café Billing System

A local, self-hosted Streamlit billing app for cafés and food service businesses.
No cloud, no subscription, no internet required after install.

---

## Features

- **Token-based billing** — each table, counter slot, or takeaway order gets a token
- **Persistent orders** — open orders survive server restart and browser refresh (SQLite)
- **Multi-cashier safe** — WAL-mode SQLite allows concurrent reads without locking
- **Three access levels** — Cashier (no password), Owner dashboard, Developer settings
- **Receipt integrity check** — Owner dashboard flags any CSV files deleted from disk
- **OS-aware receipts** — Windows: browser download button · Linux/Mac: saved to disk
- **Dynamic menu** — add, price, enable/disable items; out-of-stock toggle per item
- **Token types** — Dine-In 🪑 · Takeaway 🥡 · Delivery 🛵 · Online 💻
- **Payment methods** — Cash, Card, UPI, Online (configurable)
- **Auto-migrating config** — adding a new setting never breaks existing installations
- **Responsive UI** — works on desktop, tablet, and mobile browsers

---

## Project Structure

```
cafe_billing_system/
├── app.py                  # Entry point — orchestration only, no business logic
├── ui.py                   # Pure rendering layer — no DB calls
├── db.py                   # SQLite persistence — all DB access goes here
├── config.py               # JSON config with auto-migration
├── requirements.txt
│
├── cafe.db                 # Created on first run (SQLite)
├── cafe_settings.json      # Created on first run (auto-migrated on every start)
├── owner_password.hash     # Created during first-run setup wizard
├── owner_password_expiry.txt
├── dev_password.hash       # Created during first-run setup wizard
├── dev_password_expiry.txt
│
├── bills/                  # CSV receipts (Linux/Mac) + backup copies
├── audit_logs/             # Reserved for future audit trail exports
└── menu_items.csv          # Optional — imported once on first run if present
```

---

## Setup

### Requirements

- Python 3.10 or higher
- pip

### Install

```bash
git clone <your-repo-url>
cd cafe_billing_system

python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### Run

```bash
streamlit run app.py
```

Open `http://localhost:8501` in your browser.

---

## First Run

On first launch the app shows a two-step setup wizard before anything else:

1. **Owner password** — used to access the Owner Dashboard (transactions, tokens, menu)
2. **Developer password** — used to unlock the Settings tab inside the dashboard

Both must be set before the app starts. Keep them separate and written down somewhere safe — there is no password recovery (just delete the `.hash` files and re-run to reset).

---

## Access Levels

| Role | How to access | What they can do |
|---|---|---|
| **Cashier** | No password | Open billing tab, add items, process payments |
| **Owner** | Owner password via sidebar button | View transactions, manage tokens, manage menu |
| **Developer** | Dev password inside Owner Dashboard → Settings tab | Change system config: currency, tax rate, token prefix, session timeouts, payment methods, password policy |

Session timeouts are configurable per role (default: Owner 60 min, Developer 30 min). Set to `0` to never expire.

---

## Migrating an Existing Installation

Drop the four Python files (`app.py`, `ui.py`, `db.py`, `config.py`) and `requirements.txt` into your existing folder. On next startup:

- `cafe_settings.json` — any new settings keys are added automatically, existing values untouched
- `cafe.db` — schema uses `CREATE TABLE IF NOT EXISTS`, existing data is safe
- Password files — untouched, existing passwords still work
- `menu_items.csv` — only imported if no menu items exist in the DB yet

No manual migration steps required.

---

## Receipt Behaviour

| OS | Behaviour |
|---|---|
| **Windows** | After payment a download button appears — click to save the CSV via the browser |
| **Linux / Mac** | CSV is written directly to the `bills/` folder (and a backup copy kept there too) |

The Owner Dashboard → Transactions tab shows a **Missing Receipts** panel if any CSV files have been deleted or moved. The database record is always the source of truth — deleting a CSV file does not delete the transaction.

---

## Configuration

All settings live in `cafe_settings.json` and can be changed via the Developer Settings tab at runtime. The file is auto-created with defaults on first run and auto-updated when new settings are added in future versions.

Key settings:

| Key | Default | Description |
|---|---|---|
| `cafe_name` | CafeBoss | Displayed in header and receipts |
| `currency_symbol` | ₹ | Prefix for all prices |
| `token_count` | 10 | Minimum tokens to create on startup |
| `token_label_prefix` | Token | Label prefix, e.g. "Table" → Table 1 |
| `tokens_per_row` | 5 | Sidebar grid column count |
| `default_tax_rate` | 0.0 | Default tax % (per-item override available) |
| `payment_methods` | cash, card, upi, online | Shown in payment dropdown |
| `confirm_before_payment` | true | Show confirmation step before closing bill |
| `save_csv_receipt` | true | Write CSV file on payment |
| `owner_session_timeout_mins` | 60 | 0 = never expire |
| `dev_session_timeout_mins` | 30 | 0 = never expire |
| `password_expiry_days` | 30 | 0 = never expire |

---

## Menu Import

If you have an existing `menu_items.csv` in the project folder, it will be imported into the database on first run. Expected columns:

```
Item, Price, Category
```

Items already in the database (matched by name, case-insensitive) are skipped. After import the CSV is no longer needed — all menu management happens via the dashboard.

---

## Dependencies

| Package | Version | Purpose |
|---|---|---|
| `streamlit` | ≥ 1.35.0 | Web UI framework |
| `pandas` | ≥ 2.0.0 | Dataframe display in dashboard |

Python's standard library (`sqlite3`, `csv`, `hashlib`, `hmac`, `json`, `pathlib`, `platform`, `secrets`, `tempfile`) handles everything else — no extra installs needed.

---

## Security Notes

- Passwords are stored as `salt$sha256(salt+password)` — never in plaintext
- All comparisons use `hmac.compare_digest` to prevent timing attacks
- Only keys present in `DEFAULTS` can be written to `cafe_settings.json` — protects against config injection
- The Developer password gate is enforced at both the UI layer and the callback layer
- There is no network exposure beyond the local Streamlit server — no data leaves the machine

---

## Roadmap (schema ready, not yet wired)

- **Cashier accounts** — PIN-based login, per-cashier bill tracking (`users` table exists)
- **Per-item tax** — `tax_rate` column already in `menu_items`; needs UI and receipt calc
- **Discounts** — `discount` column already in `bills` table
- **Date range reports** — `BillService.get_range()` already implemented; needs dashboard tab
- **Token reassignment** — change token label/type without losing history
