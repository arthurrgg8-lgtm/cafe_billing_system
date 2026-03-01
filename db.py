"""
db.py — CafeBoss persistence layer
Single SQLite file (cafe.db) for all runtime state.

Tables:
  tokens        — serving units (tables, counters, takeaway slots)
  active_orders — live line items per token (survives refresh / server restart)
  bills         — closed/paid orders, append-only, UUID primary key
  bill_items    — line items belonging to a closed bill
  menu_items    — menu with stable item_id, availability flag, per-item tax
  users         — staff accounts (schema ready, auth optional for now)

All writes go through service methods — no raw SQL outside this file.
WAL mode: multiple readers + one writer without blocking.
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

SCHEMA = """
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
    notes          TEXT
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
"""


def init_db() -> None:
    """Create all tables. Safe to call on every startup (IF NOT EXISTS)."""
    with _conn() as con:
        con.executescript(SCHEMA)


# ──────────────────────────────────────────────────────────────────────────────
# TOKEN SERVICE
# ──────────────────────────────────────────────────────────────────────────────

class TokenService:

    @staticmethod
    def bootstrap_tokens(count: int, label_prefix: str = "Token") -> None:
        """
        Ensure at least `count` tokens exist.
        Existing tokens are never touched. Only adds new ones.
        """
        with _conn() as con:
            existing = con.execute("SELECT COUNT(*) FROM tokens").fetchone()[0]
            for i in range(existing + 1, count + 1):
                con.execute(
                    "INSERT INTO tokens (id, label, type) VALUES (?, ?, 'dine_in')",
                    (i, f"{label_prefix} {i}"),
                )

    @staticmethod
    def add_token(label: str, token_type: str = "dine_in") -> int:
        """Add a new token. Returns its assigned id."""
        with _conn() as con:
            new_id = con.execute(
                "SELECT COALESCE(MAX(id), 0) + 1 FROM tokens"
            ).fetchone()[0]
            con.execute(
                "INSERT INTO tokens (id, label, type) VALUES (?, ?, ?)",
                (new_id, label, token_type),
            )
            return new_id

    @staticmethod
    def get_all() -> list[dict[str, Any]]:
        with _conn() as con:
            rows = con.execute(
                "SELECT * FROM tokens WHERE enabled = 1 ORDER BY id"
            ).fetchall()
            return [dict(r) for r in rows]

    @staticmethod
    def get(token_id: int) -> dict[str, Any] | None:
        with _conn() as con:
            row = con.execute(
                "SELECT * FROM tokens WHERE id = ?", (token_id,)
            ).fetchone()
            return dict(row) if row else None

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
                    "UPDATE tokens SET active = 1, opened_at = COALESCE(opened_at, ?) WHERE id = ?",
                    (ts, token_id),
                )
            else:
                con.execute(
                    "UPDATE tokens SET active = 0, opened_at = NULL WHERE id = ?",
                    (token_id,),
                )

    @staticmethod
    def get_status_map() -> dict[int, bool]:
        with _conn() as con:
            rows = con.execute(
                "SELECT id, active FROM tokens WHERE enabled = 1"
            ).fetchall()
            return {r["id"]: bool(r["active"]) for r in rows}

    @staticmethod
    def delete(token_id: int) -> None:
        """Hard delete. Cascades to active_orders."""
        with _conn() as con:
            con.execute("DELETE FROM tokens WHERE id = ?", (token_id,))


# ──────────────────────────────────────────────────────────────────────────────
# ORDER SERVICE
# ──────────────────────────────────────────────────────────────────────────────

class OrderService:

    @staticmethod
    def get_items(token_id: int) -> list[dict[str, Any]]:
        with _conn() as con:
            rows = con.execute(
                "SELECT * FROM active_orders WHERE token_id = ? ORDER BY added_at",
                (token_id,),
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
                   (token_id, item_name, item_id, category, unit_price,
                    quantity, subtotal, cashier_id, added_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (token_id, item_name, item_id, category,
                 unit_price, quantity, subtotal, cashier_id, now),
            )
            con.execute(
                "UPDATE tokens SET active = 1, opened_at = COALESCE(opened_at, ?) WHERE id = ?",
                (now, token_id),
            )

    @staticmethod
    def remove_item(order_line_id: int) -> None:
        with _conn() as con:
            row = con.execute(
                "SELECT token_id FROM active_orders WHERE id = ?", (order_line_id,)
            ).fetchone()
            if not row:
                return
            token_id = row["token_id"]
            con.execute("DELETE FROM active_orders WHERE id = ?", (order_line_id,))
            remaining = con.execute(
                "SELECT COUNT(*) FROM active_orders WHERE token_id = ?", (token_id,)
            ).fetchone()[0]
            if remaining == 0:
                con.execute(
                    "UPDATE tokens SET active = 0, opened_at = NULL WHERE id = ?",
                    (token_id,),
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
                "SELECT COALESCE(SUM(subtotal), 0) FROM active_orders WHERE token_id = ?",
                (token_id,),
            ).fetchone()
            return round(float(row[0]), 2)


# ──────────────────────────────────────────────────────────────────────────────
# BILL SERVICE
# ──────────────────────────────────────────────────────────────────────────────

class BillService:

    @staticmethod
    def close_bill(
        token_id: int,
        token_label: str,
        token_type: str,
        items: list[dict[str, Any]],
        total: float,
        payment_method: str = "cash",
        discount: float = 0.0,
        tax: float = 0.0,
        cashier_id: int | None = None,
        filename: str | None = None,
        notes: str | None = None,
    ) -> str:
        """Write a closed bill + line items. Returns the UUID bill id."""
        bill_id = str(uuid.uuid4())
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with _conn() as con:
            con.execute(
                """INSERT INTO bills
                   (id, token_id, token_label, token_type, total, discount, tax,
                    payment_method, cashier_id, filename, paid_at, notes)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (bill_id, token_id, token_label, token_type,
                 total, discount, tax, payment_method,
                 cashier_id, filename, now, notes),
            )
            for item in items:
                con.execute(
                    """INSERT INTO bill_items
                       (bill_id, item_name, item_id, category,
                        unit_price, quantity, subtotal)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        bill_id,
                        item.get("item_name", item.get("Item", "")),
                        item.get("item_id"),
                        item.get("category", item.get("Category", "")),
                        item.get("unit_price", item.get("Price", 0)),
                        item.get("quantity",   item.get("Quantity", 1)),
                        item.get("subtotal",   item.get("Subtotal", 0)),
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
    def get_today_bills() -> list[dict[str, Any]]:
        today = datetime.now().strftime("%Y-%m-%d")
        with _conn() as con:
            rows = con.execute(
                "SELECT * FROM bills WHERE paid_at LIKE ? ORDER BY paid_at DESC",
                (f"{today}%",),
            ).fetchall()
            return [dict(r) for r in rows]

    @staticmethod
    def get_today_stats() -> tuple[int, float]:
        today = datetime.now().strftime("%Y-%m-%d")
        with _conn() as con:
            row = con.execute(
                "SELECT COUNT(*), COALESCE(SUM(total), 0) FROM bills WHERE paid_at LIKE ?",
                (f"{today}%",),
            ).fetchone()
            return int(row[0]), round(float(row[1]), 2)

    @staticmethod
    def get_bill_items(bill_id: str) -> list[dict[str, Any]]:
        with _conn() as con:
            rows = con.execute(
                "SELECT * FROM bill_items WHERE bill_id = ?", (bill_id,)
            ).fetchall()
            return [dict(r) for r in rows]

    @staticmethod
    def get_range(start: str, end: str) -> list[dict[str, Any]]:
        with _conn() as con:
            rows = con.execute(
                """SELECT * FROM bills
                   WHERE paid_at >= ? AND paid_at <= ?
                   ORDER BY paid_at DESC""",
                (f"{start} 00:00:00", f"{end} 23:59:59"),
            ).fetchall()
            return [dict(r) for r in rows]

    @staticmethod
    def find_missing_receipts(
        primary_folder: Path,
        backup_folder: Path,
        date: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Return bills whose CSV receipt cannot be found on disk.
        Checks both primary_folder and backup_folder.
        Bills with filename=NULL are skipped (receipt writing was disabled).
        Each returned dict has an extra 'expected_paths': [str, str] key.
        """
        date_filter = date or datetime.now().strftime("%Y-%m-%d")
        with _conn() as con:
            rows = con.execute(
                """SELECT id, token_label, total, payment_method, paid_at, filename
                   FROM bills
                   WHERE paid_at LIKE ? AND filename IS NOT NULL
                   ORDER BY paid_at DESC""",
                (f"{date_filter}%",),
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
        """
        Reconstruct CSV receipt as in-memory string from DB records.
        Used for st.download_button — works even if the file on disk was deleted.
        """
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
                bill["token_label"],
                i["item_name"],
                i["quantity"],
                i["unit_price"],
                i["subtotal"],
            ])
        w.writerow(["", "", "", "TOTAL",   bill["total"]])
        w.writerow(["", "", "", "PAYMENT", bill["payment_method"].upper()])
        w.writerow(["", "", "", "PAID AT", bill["paid_at"]])
        w.writerow(["", "", "", "BILL ID", bill["id"][:8].upper()])
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
    def add(name: str, price: float, category: str, tax_rate: float = 0.0) -> str:
        if not name.strip() or price <= 0:
            raise ValueError("Item name must be non-empty and price must be positive.")
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
        """
        Bulk-import from legacy menu_items.csv.
        Skips names that already exist (case-insensitive).
        Returns count of newly inserted rows.
        """
        import pandas as pd
        df = pd.read_csv(path)
        if df.empty:
            return 0
        count = 0
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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