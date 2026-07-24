"""
Асинхронный слой работы с SQLite (через aiosqlite).
Хранит траты пользователей: сумма, категория, описание, дата.
"""

import aiosqlite
from datetime import datetime, date
from config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    amount REAL NOT NULL,
    category TEXT NOT NULL,
    description TEXT,
    transaction_type TEXT NOT NULL DEFAULT 'expense',
    manual_category TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS category_limits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    category TEXT NOT NULL,
    limit_amount REAL NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(user_id, category)
);

CREATE TABLE IF NOT EXISTS recurring_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    description TEXT NOT NULL,
    amount REAL NOT NULL,
    category TEXT NOT NULL,
    interval TEXT NOT NULL DEFAULT 'monthly',
    next_due_date TEXT NOT NULL,
    last_processed_at TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_expenses_user_date
ON expenses (user_id, created_at);
"""


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(SCHEMA)

        columns = {row[1] for row in await db.execute_fetchall("PRAGMA table_info(expenses)")}
        if "transaction_type" not in columns:
            await db.execute("ALTER TABLE expenses ADD COLUMN transaction_type TEXT NOT NULL DEFAULT 'expense'")
        if "manual_category" not in columns:
            await db.execute("ALTER TABLE expenses ADD COLUMN manual_category TEXT")

        await db.commit()


async def add_transaction(
    user_id: int,
    amount: float,
    category: str,
    description: str,
    transaction_type: str = "expense",
) -> int:
    now = datetime.now().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO expenses (user_id, amount, category, description, transaction_type, manual_category, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, amount, category, description, transaction_type, category, now),
        )
        await db.commit()
        return cursor.lastrowid


async def add_expense(user_id: int, amount: float, category: str, description: str) -> int:
    return await add_transaction(user_id, amount, category, description, "expense")


async def update_entry_category(entry_id: int, category: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE expenses SET category = ?, manual_category = ? WHERE id = ?",
            (category, category, entry_id),
        )
        await db.commit()


async def delete_last_expense(user_id: int) -> tuple | None:
    """Удаляет последнюю запись пользователя и возвращает её данные (или None)."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT id, amount, category, description FROM expenses WHERE user_id = ? ORDER BY id DESC LIMIT 1",
            (user_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        await db.execute("DELETE FROM expenses WHERE id = ?", (row["id"],))
        await db.commit()
        return (row["amount"], row["category"], row["description"])


async def delete_all_user_data(user_id: int) -> int:
    """Удаляет все записи, лимиты и повторяющиеся правила пользователя."""
    async with aiosqlite.connect(DB_PATH) as db:
        deleted_expenses = await db.execute(
            "DELETE FROM expenses WHERE user_id = ?",
            (user_id,),
        )
        await db.execute("DELETE FROM category_limits WHERE user_id = ?", (user_id,))
        await db.execute("DELETE FROM recurring_rules WHERE user_id = ?", (user_id,))
        await db.commit()
        return deleted_expenses.rowcount


async def get_month_transactions(user_id: int, year: int, month: int) -> list[tuple]:
    start = date(year, month, 1).isoformat()
    if month == 12:
        end = date(year + 1, 1, 1).isoformat()
    else:
        end = date(year, month + 1, 1).isoformat()

    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT id, amount, category, description, transaction_type, created_at FROM expenses "
            "WHERE user_id = ? AND created_at >= ? AND created_at < ? ORDER BY created_at",
            (user_id, start, end),
        )
        return await cursor.fetchall()


async def get_history(user_id: int, year: int, month: int) -> list[tuple]:
    start = date(year, month, 1).isoformat()
    if month == 12:
        end = date(year + 1, 1, 1).isoformat()
    else:
        end = date(year, month + 1, 1).isoformat()

    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT id, amount, category, description, transaction_type, created_at FROM expenses "
            "WHERE user_id = ? AND created_at >= ? AND created_at < ? ORDER BY created_at DESC",
            (user_id, start, end),
        )
        return await cursor.fetchall()


async def get_month_expenses(user_id: int, year: int, month: int) -> list[tuple]:
    rows = await get_month_transactions(user_id, year, month)
    return [row for row in rows if row[4] == "expense"]


async def get_category_totals(user_id: int, year: int, month: int) -> dict[str, float]:
    rows = await get_month_expenses(user_id, year, month)
    totals: dict[str, float] = {}
    for amount, category, _desc, _created in [(row[1], row[2], row[3], row[5]) for row in rows]:
        totals[category] = totals.get(category, 0.0) + amount
    return totals


async def get_category_month_total(user_id: int, category: str, year: int, month: int) -> float:
    rows = await get_month_expenses(user_id, year, month)
    return sum(row[1] for row in rows if row[2] == category)


async def set_category_limit(user_id: int, category: str, limit_amount: float) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO category_limits (user_id, category, limit_amount, created_at) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(user_id, category) DO UPDATE SET limit_amount = excluded.limit_amount",
            (user_id, category, limit_amount, datetime.now().isoformat()),
        )
        await db.commit()


async def remove_category_limit(user_id: int, category: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM category_limits WHERE user_id = ? AND category = ?",
            (user_id, category),
        )
        await db.commit()
        return cursor.rowcount > 0


async def get_category_limit(user_id: int, category: str) -> float | None:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT limit_amount FROM category_limits WHERE user_id = ? AND category = ?",
            (user_id, category),
        )
        row = await cursor.fetchone()
        return None if row is None else float(row[0])


async def list_category_limits(user_id: int, year: int, month: int) -> list[tuple]:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT category, limit_amount FROM category_limits WHERE user_id = ? ORDER BY category",
            (user_id,),
        )
        limits = await cursor.fetchall()

    rows = await get_month_expenses(user_id, year, month)
    totals = {}
    for row in rows:
        totals[row[2]] = totals.get(row[2], 0.0) + row[1]

    result = []
    for category, limit_amount in limits:
        current = totals.get(category, 0.0)
        result.append((category, float(limit_amount), current, float(limit_amount) - current))
    return result


async def add_recurring_rule(user_id: int, description: str, amount: float, category: str, interval: str = "monthly") -> int:
    now = datetime.now().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO recurring_rules (user_id, description, amount, category, interval, next_due_date, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, description, amount, category, interval, date.today().isoformat(), now),
        )
        await db.commit()
        return cursor.lastrowid


async def list_recurring_rules(user_id: int) -> list[tuple]:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT id, description, amount, category, interval, next_due_date FROM recurring_rules WHERE user_id = ? ORDER BY id",
            (user_id,),
        )
        return await cursor.fetchall()


async def get_due_recurring_rules(today: date) -> list[tuple]:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT id, user_id, description, amount, category FROM recurring_rules WHERE next_due_date <= ?",
            (today.isoformat(),),
        )
        return await cursor.fetchall()


async def advance_recurring_rule(rule_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        today = date.today()
        next_month = today.month + 1 if today.month < 12 else 1
        next_year = today.year if today.month < 12 else today.year + 1
        next_due = date(next_year, next_month, today.day).isoformat()
        await db.execute(
            "UPDATE recurring_rules SET next_due_date = ?, last_processed_at = ? WHERE id = ?",
            (next_due, datetime.now().isoformat(), rule_id),
        )
        await db.commit()
