"""
db.py — CafeBoss persistence layer

Changes in this version:
  - bills table gets work_date TEXT column (the cashier's selected working date)
    paid_at stays as real wall-clock timestamp — work_date is what all filtering uses
  - Schema migration: ALTER TABLE adds work_date if missing, backfills from DATE(paid_at)
  - BillService.close_bill() accepts work_date param
  - BillService.get_bills_by_date(work_date) and get_stats_by_date(work_date)
  - BillService.find_missing_receipts() takes work_date — checks only that date's files
  - MenuDB.update_tax_rate() — dev can set per-item tax rate
  - OrderService.has_any_open_orders() — used to block date change if orders are open
  - CSV filenames embed work_date: bill_{work_date}_{bill_id[:8]}.csv
    zero cross-date collisions, owner can see date at a glance in bills/ folder
"""

from __future__ import annotations

import csv as _csv
import io
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Generator

DB_PATH = Path("cafe.db")


# ──────────────────────────────────────────────────────────────────────────────
# CONNECTION
# ──────────────────────────────────────────────────────────────────────────────

@contextmanager
def _conn() -> Generator[sqlite3.Connection, None, None]:
    con = sqlite3.connect(DB_PATH, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA foreign_keys=ON")
    con.execute("PRAGMA busy_timeout=5000")
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


# ──────────────────────────────────────────────────────────────────────────────
# SCHEMA
# ──────────────────────────────────────────────────────────────────────────────

_CREATE_SCHEMA = """
CREATE TABLE IF NOT EXISTS tokens (
    id          INTEGER PRIMARY KEY,
    label       TEXT    NOT NULL,
    type        TEXT    NOT NULL DEFAULT 'dine_in',
    active      INTEGER NOT NULL DEFAULT 0,
    enabled     INTEGER NOT NULL DEFAULT 1,
    opened_at   TEXT,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS active_orders (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    token_id    INTEGER NOT NULL REFERENCES tokens(id) ON DELETE CASCADE,
    item_name   TEXT    NOT NULL,
    item_id     TEXT,
    category    TEXT,
    unit_price  REAL    NOT NULL,
    quantity    INTEGER NOT NULL DEFAULT 1,
    subtotal    REAL    NOT NULL,
    prep_status TEXT    NOT NULL DEFAULT 'new',
    cashier_id  INTEGER,
    added_at    TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS bills (
    id             TEXT    PRIMARY KEY,
    token_id       INTEGER NOT NULL,
    token_label    TEXT    NOT NULL,
    token_type     TEXT    NOT NULL,
    total          REAL    NOT NULL,
    discount       REAL    NOT NULL DEFAULT 0,
    tax            REAL    NOT NULL DEFAULT 0,
    payment_method TEXT    NOT NULL DEFAULT 'cash',
    cashier_id     INTEGER,
    filename       TEXT,
    paid_at        TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
    work_date      TEXT,
    notes          TEXT,
    customer_rating INTEGER,
    customer_review TEXT,
    reviewed_at     TEXT
);

CREATE TABLE IF NOT EXISTS bill_items (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    bill_id     TEXT    NOT NULL REFERENCES bills(id) ON DELETE CASCADE,
    item_name   TEXT    NOT NULL,
    item_id     TEXT,
    category    TEXT,
    unit_price  REAL    NOT NULL,
    quantity    INTEGER NOT NULL,
    subtotal    REAL    NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL,
    role        TEXT    NOT NULL DEFAULT 'cashier',
    pin_hash    TEXT,
    active      INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS menu_items (
    item_id     TEXT    PRIMARY KEY DEFAULT (lower(hex(randomblob(4)))),
    name        TEXT    NOT NULL,
    price       REAL    NOT NULL,
    category    TEXT    NOT NULL DEFAULT 'Uncategorised',
    available   INTEGER NOT NULL DEFAULT 1,
    tax_rate    REAL    NOT NULL DEFAULT 0,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE INDEX IF NOT EXISTS idx_active_orders_token_id ON active_orders(token_id);
CREATE INDEX IF NOT EXISTS idx_bills_work_date ON bills(work_date);
CREATE INDEX IF NOT EXISTS idx_bills_paid_at ON bills(paid_at);
"""

# Columns added after initial deploy — applied via ALTER TABLE if missing
_MIGRATIONS = [
    # (table, column, definition)
    ("bills", "work_date", "TEXT"),
    ("active_orders", "prep_status", "TEXT NOT NULL DEFAULT 'new'"),
    ("bills", "customer_rating", "INTEGER"),
    ("bills", "customer_review", "TEXT"),
    ("bills", "reviewed_at", "TEXT"),
]


def init_db() -> None:
    """
    Create all tables (IF NOT EXISTS) then apply any missing column migrations.
    Also backfills work_date = DATE(paid_at) for any rows that have NULL work_date.
    Safe to call on every startup.
    """
    with _conn() as con:
        con.executescript(_CREATE_SCHEMA)

        # Column-level migrations — ALTER TABLE only runs if column is missing
        existing_cols: dict[str, set[str]] = {}
        for table, col, defn in _MIGRATIONS:
            if table not in existing_cols:
                rows = con.execute(f"PRAGMA table_info({table})").fetchall()
                existing_cols[table] = {r["name"] for r in rows}
            if col not in existing_cols[table]:
                con.execute(
                    f"ALTER TABLE {table} ADD COLUMN {col} {defn}"
                )
                existing_cols[table].add(col)

        # Backfill: any bill with NULL work_date gets DATE(paid_at)
        con.execute(
            "UPDATE bills SET work_date = DATE(paid_at) WHERE work_date IS NULL"
        )


# ──────────────────────────────────────────────────────────────────────────────
# TOKEN SERVICE
# ──────────────────────────────────────────────────────────────────────────────

class TokenService:

    @staticmethod
    def bootstrap_tokens(count: int, label_prefix: str = "Token",
                         token_max: int = 50) -> None:
        """
        Ensure at least `count` tokens exist, up to token_max hard cap.
        Existing tokens are never touched.
        """
        with _conn() as con:
            target   = min(count, token_max)
            existing = con.execute("SELECT COUNT(*) FROM tokens").fetchone()[0]
            for _ in range(existing, target):
                next_id = con.execute(
                    "SELECT COALESCE(MAX(id), 0) + 1 FROM tokens"
                ).fetchone()[0]
                con.execute(
                    "INSERT INTO tokens (id, label, type) VALUES (?, ?, 'dine_in')",
                    (next_id, f"{label_prefix} {next_id}"),
                )

    @staticmethod
    def add_token(label: str, token_type: str = "dine_in",
                  token_max: int = 50) -> tuple[bool, str]:
        """
        Add a new token. Returns (success, message).
        Fails if total token count would exceed token_max.
        """
        with _conn() as con:
            total = con.execute("SELECT COUNT(*) FROM tokens").fetchone()[0]
            if total >= token_max:
                return False, f"Token cap of {token_max} reached. Ask the developer to raise the limit."
            cur = con.execute(
                "INSERT INTO tokens (label, type) VALUES (?, ?)",
                (label, token_type),
            )
            new_id = int(cur.lastrowid)
            return True, f"Token '{label}' added (id {new_id})."

    @staticmethod
    def get_all() -> list[dict[str, Any]]:
        with _conn() as con:
            rows = con.execute(
                "SELECT * FROM tokens WHERE enabled = 1 ORDER BY id"
            ).fetchall()
            return [dict(r) for r in rows]

    @staticmethod
    def get_all_including_disabled() -> list[dict[str, Any]]:
        with _conn() as con:
            rows = con.execute("SELECT * FROM tokens ORDER BY id").fetchall()
            return [dict(r) for r in rows]

    @staticmethod
    def get(token_id: int) -> dict[str, Any] | None:
        with _conn() as con:
            row = con.execute(
                "SELECT * FROM tokens WHERE id = ?", (token_id,)
            ).fetchone()
            return dict(row) if row else None

    @staticmethod
    def count() -> int:
        with _conn() as con:
            return con.execute("SELECT COUNT(*) FROM tokens").fetchone()[0]

    @staticmethod
    def update_label(token_id: int, label: str) -> None:
        with _conn() as con:
            con.execute("UPDATE tokens SET label = ? WHERE id = ?", (label, token_id))

    @staticmethod
    def update_type(token_id: int, token_type: str) -> None:
        with _conn() as con:
            con.execute("UPDATE tokens SET type = ? WHERE id = ?", (token_type, token_id))

    @staticmethod
    def set_enabled(token_id: int, enabled: bool) -> None:
        with _conn() as con:
            con.execute(
                "UPDATE tokens SET enabled = ? WHERE id = ?",
                (1 if enabled else 0, token_id),
            )

    @staticmethod
    def set_active(token_id: int, active: bool, opened_at: str | None = None) -> None:
        with _conn() as con:
            if active:
                ts = opened_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                con.execute(
                    "UPDATE tokens SET active = 1, "
                    "opened_at = COALESCE(opened_at, ?) WHERE id = ?",
                    (ts, token_id),
                )
            else:
                con.execute(
                    "UPDATE tokens SET active = 0, opened_at = NULL WHERE id = ?",
                    (token_id,),
                )

    @staticmethod
    def delete(token_id: int) -> None:
        """Hard delete. Cascades to active_orders."""
        with _conn() as con:
            con.execute("DELETE FROM tokens WHERE id = ?", (token_id,))


# ──────────────────────────────────────────────────────────────────────────────
# ORDER SERVICE
# ──────────────────────────────────────────────────────────────────────────────

class OrderService:
    _PREP_STAGES = {"new", "preparing", "ready"}

    @staticmethod
    def get_items(token_id: int) -> list[dict[str, Any]]:
        with _conn() as con:
            rows = con.execute(
                "SELECT * FROM active_orders WHERE token_id = ? ORDER BY added_at",
                (token_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    @staticmethod
    def get_kitchen_snapshot() -> list[dict[str, Any]]:
        with _conn() as con:
            rows = con.execute(
                """SELECT ao.id, ao.token_id, ao.item_name, ao.quantity, ao.added_at,
                          ao.prep_status, t.label AS token_label, t.type AS token_type
                   FROM active_orders ao
                   JOIN tokens t ON t.id = ao.token_id
                   WHERE t.enabled = 1
                   ORDER BY ao.added_at ASC, ao.id ASC"""
            ).fetchall()
            return [dict(r) for r in rows]

    @staticmethod
    def add_item(
        token_id: int,
        item_name: str,
        unit_price: float,
        quantity: int,
        category: str = "",
        item_id: str | None = None,
        cashier_id: int | None = None,
    ) -> None:
        subtotal = round(unit_price * quantity, 2)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with _conn() as con:
            con.execute(
                """INSERT INTO active_orders
                   (token_id, item_name, item_id, category,
                    unit_price, quantity, subtotal, prep_status, cashier_id, added_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 'new', ?, ?)""",
                (token_id, item_name, item_id, category,
                 unit_price, quantity, subtotal, cashier_id, now),
            )
            con.execute(
                "UPDATE tokens SET active = 1, "
                "opened_at = COALESCE(opened_at, ?) WHERE id = ?",
                (now, token_id),
            )

    @staticmethod
    def remove_item(order_line_id: int) -> None:
        with _conn() as con:
            row = con.execute(
                "SELECT token_id FROM active_orders WHERE id = ?",
                (order_line_id,),
            ).fetchone()
            if not row:
                return
            token_id = row["token_id"]
            con.execute("DELETE FROM active_orders WHERE id = ?", (order_line_id,))
            remaining = con.execute(
                "SELECT COUNT(*) FROM active_orders WHERE token_id = ?",
                (token_id,),
            ).fetchone()[0]
            if remaining == 0:
                con.execute(
                    "UPDATE tokens SET active = 0, opened_at = NULL WHERE id = ?",
                    (token_id,),
                )

    @staticmethod
    def set_prep_status(order_line_id: int, prep_status: str) -> None:
        status = prep_status.strip().lower()
        if status not in OrderService._PREP_STAGES:
            raise ValueError(f"Invalid prep status: {prep_status}")
        with _conn() as con:
            con.execute(
                "UPDATE active_orders SET prep_status = ? WHERE id = ?",
                (status, order_line_id),
            )

    @staticmethod
    def clear_token(token_id: int) -> None:
        with _conn() as con:
            con.execute("DELETE FROM active_orders WHERE token_id = ?", (token_id,))
            con.execute(
                "UPDATE tokens SET active = 0, opened_at = NULL WHERE id = ?",
                (token_id,),
            )

    @staticmethod
    def get_total(token_id: int) -> float:
        with _conn() as con:
            row = con.execute(
                "SELECT COALESCE(SUM(subtotal), 0) "
                "FROM active_orders WHERE token_id = ?",
                (token_id,),
            ).fetchone()
            return round(float(row[0]), 2)

    @staticmethod
    def has_any_open_orders() -> bool:
        """True if ANY token currently has items in active_orders."""
        with _conn() as con:
            count = con.execute(
                "SELECT COUNT(*) FROM active_orders"
            ).fetchone()[0]
            return count > 0

    @staticmethod
    def get_open_token_count() -> int:
        """Number of distinct tokens with open orders."""
        with _conn() as con:
            return con.execute(
                "SELECT COUNT(DISTINCT token_id) FROM active_orders"
            ).fetchone()[0]


# ──────────────────────────────────────────────────────────────────────────────
# BILL SERVICE
# ──────────────────────────────────────────────────────────────────────────────

class BillService:
    @staticmethod
    def get(bill_id: str) -> dict[str, Any] | None:
        with _conn() as con:
            row = con.execute(
                "SELECT * FROM bills WHERE id = ?",
                (bill_id,),
            ).fetchone()
            return dict(row) if row else None

    @staticmethod
    def save_customer_review(
        bill_id: str,
        rating: int,
        review: str,
        reviewed_at: str | None = None,
    ) -> None:
        safe_rating = max(1, min(5, int(rating)))
        safe_review = (review or "").strip()
        ts = reviewed_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with _conn() as con:
            con.execute(
                """UPDATE bills
                   SET customer_rating = ?, customer_review = ?, reviewed_at = ?
                   WHERE id = ?""",
                (safe_rating, safe_review, ts, bill_id),
            )

    @staticmethod
    def close_bill(
        token_id: int,
        token_label: str,
        token_type: str,
        items: list[dict[str, Any]],
        total: float,
        work_date: str,               # cashier's selected working date YYYY-MM-DD
        payment_method: str = "cash",
        discount: float = 0.0,
        tax: float = 0.0,
        cashier_id: int | None = None,
        filename: str | None = None,
        notes: str | None = None,
        customer_rating: int | None = None,
        customer_review: str | None = None,
        reviewed_at: str | None = None,
    ) -> str:
        """Write a closed bill + line items. Returns the UUID bill id."""
        bill_id = str(uuid.uuid4())
        now     = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with _conn() as con:
            con.execute(
                """INSERT INTO bills
                   (id, token_id, token_label, token_type, total, discount, tax,
                    payment_method, cashier_id, filename, paid_at, work_date, notes,
                    customer_rating, customer_review, reviewed_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (bill_id, token_id, token_label, token_type,
                 total, discount, tax, payment_method,
                 cashier_id, filename, now, work_date, notes,
                 customer_rating, customer_review, reviewed_at),
            )
            for item in items:
                con.execute(
                    """INSERT INTO bill_items
                       (bill_id, item_name, item_id, category,
                        unit_price, quantity, subtotal)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        bill_id,
                        item.get("item_name", ""),
                        item.get("item_id"),
                        item.get("category", ""),
                        item.get("unit_price", 0),
                        item.get("quantity",   1),
                        item.get("subtotal",   0),
                    ),
                )
        return bill_id

    @staticmethod
    def update_filename(bill_id: str, filename: str) -> None:
        with _conn() as con:
            con.execute(
                "UPDATE bills SET filename = ? WHERE id = ?", (filename, bill_id)
            )

    @staticmethod
    def get_bills_by_date(work_date: str) -> list[dict[str, Any]]:
        """
        Return all bills for a given work_date (YYYY-MM-DD).
        Falls back to DATE(paid_at) for old rows that have NULL work_date.
        """
        with _conn() as con:
            rows = con.execute(
                """SELECT * FROM bills
                   WHERE COALESCE(work_date, DATE(paid_at)) = ?
                   ORDER BY paid_at DESC""",
                (work_date,),
            ).fetchall()
            return [dict(r) for r in rows]

    @staticmethod
    def get_stats_by_date(work_date: str) -> tuple[int, float]:
        with _conn() as con:
            row = con.execute(
                """SELECT COUNT(*), COALESCE(SUM(total), 0)
                   FROM bills
                   WHERE COALESCE(work_date, DATE(paid_at)) = ?""",
                (work_date,),
            ).fetchone()
            return int(row[0]), round(float(row[1]), 2)

    # Keep these for backward compat / any internal uses
    @staticmethod
    def get_today_bills() -> list[dict[str, Any]]:
        today = datetime.now().strftime("%Y-%m-%d")
        return BillService.get_bills_by_date(today)

    @staticmethod
    def get_today_stats() -> tuple[int, float]:
        today = datetime.now().strftime("%Y-%m-%d")
        return BillService.get_stats_by_date(today)

    @staticmethod
    def get_bill_items(bill_id: str) -> list[dict[str, Any]]:
        with _conn() as con:
            rows = con.execute(
                "SELECT * FROM bill_items WHERE bill_id = ?", (bill_id,)
            ).fetchall()
            return [dict(r) for r in rows]

    @staticmethod
    def get_range(start: str, end: str) -> list[dict[str, Any]]:
        """Bills where work_date is between start and end (YYYY-MM-DD inclusive)."""
        with _conn() as con:
            rows = con.execute(
                """SELECT * FROM bills
                   WHERE COALESCE(work_date, DATE(paid_at)) >= ?
                     AND COALESCE(work_date, DATE(paid_at)) <= ?
                   ORDER BY paid_at DESC""",
                (start, end),
            ).fetchall()
            return [dict(r) for r in rows]

    @staticmethod
    def get_available_dates() -> list[str]:
        """
        Return distinct work_dates that have bills, descending.
        Used to populate the owner dashboard date picker.
        """
        with _conn() as con:
            rows = con.execute(
                """SELECT DISTINCT COALESCE(work_date, DATE(paid_at)) AS d
                   FROM bills ORDER BY d DESC""",
            ).fetchall()
            return [r["d"] for r in rows]

    @staticmethod
    def find_missing_receipts(
        primary_folder: Path,
        backup_folder: Path,
        work_date: str,
    ) -> list[dict[str, Any]]:
        """
        Return bills for work_date whose CSV receipt cannot be found on disk.
        Checks both primary_folder and backup_folder.
        Bills with filename=NULL are skipped (receipt writing was disabled).

        Filenames are now work_date-prefixed: bill_{work_date}_{bill_id[:8]}.csv
        so this check only ever matches files belonging to that date — zero
        cross-date collision.
        """
        with _conn() as con:
            rows = con.execute(
                """SELECT id, token_label, total, payment_method,
                          paid_at, work_date, filename
                   FROM bills
                   WHERE COALESCE(work_date, DATE(paid_at)) = ?
                     AND filename IS NOT NULL
                   ORDER BY paid_at DESC""",
                (work_date,),
            ).fetchall()

        missing: list[dict[str, Any]] = []
        for row in rows:
            bill  = dict(row)
            fname = bill["filename"]
            paths = [Path(primary_folder) / fname, Path(backup_folder) / fname]
            if not any(p.exists() for p in paths):
                bill["expected_paths"] = [str(p) for p in paths]
                missing.append(bill)
        return missing

    @staticmethod
    def build_csv_content(bill_id: str) -> str:
        """Reconstruct CSV receipt from DB. Works even if file was deleted."""
        with _conn() as con:
            bill_row  = con.execute(
                "SELECT * FROM bills WHERE id = ?", (bill_id,)
            ).fetchone()
            item_rows = con.execute(
                "SELECT * FROM bill_items WHERE bill_id = ?", (bill_id,)
            ).fetchall()

        if not bill_row:
            return ""

        bill = dict(bill_row)
        buf  = io.StringIO()
        w    = _csv.writer(buf)
        w.writerow(["Token", "Item", "Quantity", "Unit Price", "Subtotal"])
        for item in item_rows:
            i = dict(item)
            w.writerow([
                bill["token_label"], i["item_name"],
                i["quantity"], i["unit_price"], i["subtotal"],
            ])
        w.writerow(["", "", "", "TOTAL",      bill["total"]])
        w.writerow(["", "", "", "PAYMENT",    bill["payment_method"].upper()])
        w.writerow(["", "", "", "WORK DATE",  bill.get("work_date", "")])
        w.writerow(["", "", "", "PAID AT",    bill["paid_at"]])
        if bill.get("customer_rating") is not None:
            w.writerow(["", "", "", "CUSTOMER RATING", bill.get("customer_rating", "")])
        if bill.get("customer_review"):
            w.writerow(["", "", "", "CUSTOMER REVIEW", bill.get("customer_review", "")])
        w.writerow(["", "", "", "BILL ID",    bill["id"][:8].upper()])
        return buf.getvalue()


# ──────────────────────────────────────────────────────────────────────────────
# MENU SERVICE
# ──────────────────────────────────────────────────────────────────────────────

class MenuDB:

    @staticmethod
    def get_all(available_only: bool = False) -> list[dict[str, Any]]:
        with _conn() as con:
            q = "SELECT * FROM menu_items"
            if available_only:
                q += " WHERE available = 1"
            q += " ORDER BY category, name"
            return [dict(r) for r in con.execute(q).fetchall()]

    @staticmethod
    def add(name: str, price: float, category: str,
            tax_rate: float = 0.0) -> str:
        if not name.strip() or price <= 0:
            raise ValueError("Name must be non-empty and price must be positive.")
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with _conn() as con:
            item_id = con.execute(
                "SELECT lower(hex(randomblob(4)))"
            ).fetchone()[0]
            con.execute(
                """INSERT INTO menu_items
                   (item_id, name, price, category, tax_rate, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (item_id, name.strip(), price,
                 category.strip() or "Uncategorised", tax_rate, now, now),
            )
            return item_id

    @staticmethod
    def update_price(item_id: str, new_price: float) -> None:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with _conn() as con:
            con.execute(
                "UPDATE menu_items SET price = ?, updated_at = ? WHERE item_id = ?",
                (new_price, now, item_id),
            )

    @staticmethod
    def update_tax_rate(item_id: str, tax_rate: float) -> None:
        """Dev-only: set per-item tax rate (%)."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with _conn() as con:
            con.execute(
                "UPDATE menu_items SET tax_rate = ?, updated_at = ? "
                "WHERE item_id = ?",
                (max(0.0, tax_rate), now, item_id),
            )

    @staticmethod
    def set_available(item_id: str, available: bool) -> None:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with _conn() as con:
            con.execute(
                "UPDATE menu_items SET available = ?, updated_at = ? WHERE item_id = ?",
                (1 if available else 0, now, item_id),
            )

    @staticmethod
    def delete(item_id: str) -> None:
        with _conn() as con:
            con.execute("DELETE FROM menu_items WHERE item_id = ?", (item_id,))

    @staticmethod
    def import_from_csv(path: Path) -> int:
        import pandas as pd
        df = pd.read_csv(path)
        if df.empty:
            return 0
        count = 0
        now   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with _conn() as con:
            existing = {
                r[0].lower()
                for r in con.execute("SELECT name FROM menu_items").fetchall()
            }
            for _, row in df.iterrows():
                name = str(row.get("Item", "")).strip()
                if not name or name.lower() in existing:
                    continue
                price    = float(row.get("Price", 0))
                category = str(row.get("Category", "Uncategorised")).strip()
                item_id  = con.execute(
                    "SELECT lower(hex(randomblob(4)))"
                ).fetchone()[0]
                con.execute(
                    """INSERT INTO menu_items
                       (item_id, name, price, category, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (item_id, name, price, category, now, now),
                )
                existing.add(name.lower())
                count += 1
        return count


# ──────────────────────────────────────────────────────────────────────────────
# USER SERVICE
# ──────────────────────────────────────────────────────────────────────────────

class UserService:

    @staticmethod
    def get_all() -> list[dict[str, Any]]:
        with _conn() as con:
            rows = con.execute(
                "SELECT id, name, role, active, created_at FROM users ORDER BY id"
            ).fetchall()
            return [dict(r) for r in rows]

    @staticmethod
    def add(name: str, role: str = "cashier") -> int:
        with _conn() as con:
            cur = con.execute(
                "INSERT INTO users (name, role) VALUES (?, ?)", (name, role)
            )
            return cur.lastrowid

    @staticmethod
    def set_active(user_id: int, active: bool) -> None:
        with _conn() as con:
            con.execute(
                "UPDATE users SET active = ? WHERE id = ?",
                (1 if active else 0, user_id),
            )
