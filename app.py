"""Expense Tracker REST API.

A small Flask + SQLite API to create, read, update and delete expenses.
Run it with:  python app.py   (then open http://127.0.0.1:5000/expenses)
"""

import sqlite3
from datetime import date

from flask import Flask, g, jsonify, request

DEFAULT_DB = "expenses.db"


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def get_db():
    """Open one database connection per request and reuse it."""
    if "db" not in g:
        g.db = sqlite3.connect(g.db_path)
        g.db.row_factory = sqlite3.Row  # lets us read rows like dicts
    return g.db


def init_db(db_path):
    """Create the expenses table if it does not exist yet."""
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS expenses (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT    NOT NULL,
            amount      REAL    NOT NULL,
            category    TEXT    NOT NULL,
            date        TEXT    NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


def row_to_dict(row):
    return {
        "id": row["id"],
        "description": row["description"],
        "amount": row["amount"],
        "category": row["category"],
        "date": row["date"],
    }


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

def validate_expense(data, partial=False):
    """Check the JSON body. Returns (clean_data, errors).

    partial=True is used for updates (PUT), where every field is optional
    but any field that IS sent must still be valid.
    """
    if not isinstance(data, dict):
        return None, ["Request body must be a JSON object."]

    errors = []
    clean = {}

    # description: non-empty text
    if "description" in data:
        desc = data["description"]
        if not isinstance(desc, str) or not desc.strip():
            errors.append("description must be a non-empty string.")
        else:
            clean["description"] = desc.strip()
    elif not partial:
        errors.append("description is required.")

    # amount: a positive number (bool is excluded, since True counts as 1 in Python)
    if "amount" in data:
        amount = data["amount"]
        if isinstance(amount, bool) or not isinstance(amount, (int, float)):
            errors.append("amount must be a number.")
        elif amount <= 0:
            errors.append("amount must be greater than 0.")
        else:
            clean["amount"] = round(float(amount), 2)
    elif not partial:
        errors.append("amount is required.")

    # category: non-empty text, stored in lowercase so "Food" and "food" match
    if "category" in data:
        cat = data["category"]
        if not isinstance(cat, str) or not cat.strip():
            errors.append("category must be a non-empty string.")
        else:
            clean["category"] = cat.strip().lower()
    elif not partial:
        errors.append("category is required.")

    # date: optional, must be YYYY-MM-DD; defaults to today when creating
    if "date" in data:
        d = data["date"]
        try:
            if not isinstance(d, str):
                raise ValueError
            clean["date"] = date.fromisoformat(d).isoformat()
        except ValueError:
            errors.append("date must be in YYYY-MM-DD format.")
    elif not partial:
        clean["date"] = date.today().isoformat()

    if partial and not errors and not clean:
        errors.append("Send at least one field to update.")

    return clean, errors


# ---------------------------------------------------------------------------
# App factory and routes
# ---------------------------------------------------------------------------

def create_app(db_path=DEFAULT_DB):
    app = Flask(__name__)
    init_db(db_path)

    @app.before_request
    def set_db_path():
        g.db_path = db_path

    @app.teardown_appcontext
    def close_db(exception=None):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    def not_found(expense_id):
        return jsonify({"error": f"Expense {expense_id} not found."}), 404

    # CREATE
    @app.post("/expenses")
    def create_expense():
        clean, errors = validate_expense(request.get_json(silent=True))
        if errors:
            return jsonify({"errors": errors}), 400

        db = get_db()
        # "?" placeholders keep user input out of the SQL text (no SQL injection)
        cur = db.execute(
            "INSERT INTO expenses (description, amount, category, date) VALUES (?, ?, ?, ?)",
            (clean["description"], clean["amount"], clean["category"], clean["date"]),
        )
        db.commit()
        row = db.execute("SELECT * FROM expenses WHERE id = ?", (cur.lastrowid,)).fetchone()
        return jsonify(row_to_dict(row)), 201

    # READ all (optional ?category=food filter)
    @app.get("/expenses")
    def list_expenses():
        db = get_db()
        category = request.args.get("category")
        if category:
            rows = db.execute(
                "SELECT * FROM expenses WHERE category = ? ORDER BY date, id",
                (category.strip().lower(),),
            ).fetchall()
        else:
            rows = db.execute("SELECT * FROM expenses ORDER BY date, id").fetchall()
        return jsonify([row_to_dict(r) for r in rows])

    # SUMMARY: total spent overall and per category
    @app.get("/expenses/summary")
    def summary():
        db = get_db()
        rows = db.execute(
            "SELECT category, ROUND(SUM(amount), 2) AS total FROM expenses "
            "GROUP BY category ORDER BY category"
        ).fetchall()
        by_category = {r["category"]: r["total"] for r in rows}
        return jsonify({"total": round(sum(by_category.values()), 2), "by_category": by_category})

    # READ one
    @app.get("/expenses/<int:expense_id>")
    def get_expense(expense_id):
        row = get_db().execute("SELECT * FROM expenses WHERE id = ?", (expense_id,)).fetchone()
        if row is None:
            return not_found(expense_id)
        return jsonify(row_to_dict(row))

    # UPDATE (send only the fields you want to change)
    @app.put("/expenses/<int:expense_id>")
    def update_expense(expense_id):
        db = get_db()
        if db.execute("SELECT id FROM expenses WHERE id = ?", (expense_id,)).fetchone() is None:
            return not_found(expense_id)

        clean, errors = validate_expense(request.get_json(silent=True), partial=True)
        if errors:
            return jsonify({"errors": errors}), 400

        # Column names come from our own validated keys, never from the user,
        # so building the SET part this way is safe.
        set_part = ", ".join(f"{col} = ?" for col in clean)
        db.execute(f"UPDATE expenses SET {set_part} WHERE id = ?", (*clean.values(), expense_id))
        db.commit()
        row = db.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,)).fetchone()
        return jsonify(row_to_dict(row))

    # DELETE
    @app.delete("/expenses/<int:expense_id>")
    def delete_expense(expense_id):
        db = get_db()
        cur = db.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
        db.commit()
        if cur.rowcount == 0:
            return not_found(expense_id)
        return "", 204

    return app


if __name__ == "__main__":
    create_app().run(debug=True)
