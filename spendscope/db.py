import sqlite3

from flask import current_app, g


SCHEMA = """
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    description TEXT NOT NULL,
    amount REAL NOT NULL,
    category TEXT NOT NULL,
    normalized_merchant TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_transactions_date
ON transactions(date);

CREATE INDEX IF NOT EXISTS idx_transactions_category
ON transactions(category);

CREATE TABLE IF NOT EXISTS budgets (
    category TEXT PRIMARY KEY,
    monthly_limit REAL NOT NULL CHECK (monthly_limit >= 0)
);
"""


DEFAULT_BUDGETS = {
    "Groceries": 300,
    "Dining": 180,
    "Transport": 160,
    "Entertainment": 100,
    "Shopping": 150,
}


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(app):
    with app.app_context():
        db = sqlite3.connect(app.config["DATABASE"])
        db.executescript(SCHEMA)
        for category, monthly_limit in DEFAULT_BUDGETS.items():
            db.execute(
                """
                INSERT OR IGNORE INTO budgets(category, monthly_limit)
                VALUES (?, ?)
                """,
                (category, monthly_limit),
            )
        db.commit()
        db.close()

    app.teardown_appcontext(close_db)
