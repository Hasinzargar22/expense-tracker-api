# Expense Tracker REST API

A small REST API for tracking personal expenses, built with **Python, Flask and SQLite**. It supports full create, read, update and delete (CRUD) operations, validates every input, returns clear JSON errors, and is covered by **22 pytest unit tests**.

## Features

- CRUD endpoints for expenses
- Filter expenses by category (case-insensitive)
- Summary endpoint with totals per category
- Input validation with clear error messages (missing fields, negative amounts, wrong date format, non-JSON body)
- Parameterised SQL queries, so user input can never change a query (no SQL injection)
- Each test runs on its own fresh database

## Endpoints

| Method | URL | What it does |
|--------|-----|--------------|
| POST | `/expenses` | Create an expense |
| GET | `/expenses` | List all expenses (optional `?category=food`) |
| GET | `/expenses/<id>` | Get one expense |
| PUT | `/expenses/<id>` | Update only the fields you send |
| DELETE | `/expenses/<id>` | Delete an expense |
| GET | `/expenses/summary` | Total spent, overall and per category |

### Example

```bash
curl -X POST http://127.0.0.1:5000/expenses \
     -H "Content-Type: application/json" \
     -d '{"description": "Lunch", "amount": 150, "category": "Food", "date": "2026-10-01"}'
```

Response (`201 Created`):

```json
{"id": 1, "description": "Lunch", "amount": 150.0, "category": "food", "date": "2026-10-01"}
```

Invalid input returns `400 Bad Request` with a list of every problem found:

```json
{"errors": ["amount must be greater than 0.", "date must be in YYYY-MM-DD format."]}
```

### Validation rules

| Field | Rule |
|-------|------|
| `description` | required, non-empty text |
| `amount` | required, a number greater than 0 |
| `category` | required, non-empty text (stored in lowercase) |
| `date` | optional, `YYYY-MM-DD`; defaults to today |

## Run it

```bash
pip install -r requirements.txt
python app.py
```

The API runs at `http://127.0.0.1:5000`.

## Run the tests

```bash
pytest
```

Expected result: `22 passed`.

## How it was built

Built with AI-assisted development. I reviewed, tested and corrected the generated code before committing, and the tests check edge cases such as empty bodies, invalid amounts, missing IDs and SQL-injection text.

## Tech
Python 3 · Flask · SQLite · pytest · Git
