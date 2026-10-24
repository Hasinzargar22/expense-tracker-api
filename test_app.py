"""Unit tests for the Expense Tracker API. Run with:  pytest"""

import pytest

from app import create_app


@pytest.fixture
def client(tmp_path):
    """A fresh app with its own empty database for every test."""
    app = create_app(db_path=str(tmp_path / "test.db"))
    app.config["TESTING"] = True
    return app.test_client()


def add(client, **overrides):
    body = {"description": "Lunch", "amount": 150, "category": "Food", "date": "2026-10-01"}
    body.update(overrides)
    return client.post("/expenses", json=body)


# ---------- CREATE ----------

def test_create_returns_201_and_the_new_expense(client):
    res = add(client)
    assert res.status_code == 201
    data = res.get_json()
    assert data["id"] == 1
    assert data["description"] == "Lunch"
    assert data["amount"] == 150.0
    assert data["category"] == "food"  # stored in lowercase


def test_create_without_date_uses_today(client):
    res = client.post("/expenses", json={"description": "Bus", "amount": 20, "category": "travel"})
    assert res.status_code == 201
    assert len(res.get_json()["date"]) == 10  # YYYY-MM-DD


def test_create_missing_fields_returns_400_with_all_errors(client):
    res = client.post("/expenses", json={})
    assert res.status_code == 400
    errors = res.get_json()["errors"]
    assert len(errors) == 3  # description, amount and category are all required


@pytest.mark.parametrize("bad_amount", [0, -5, "100", None, True])
def test_create_rejects_bad_amounts(client, bad_amount):
    res = add(client, amount=bad_amount)
    assert res.status_code == 400


def test_create_rejects_bad_date(client):
    res = add(client, date="01-10-2026")
    assert res.status_code == 400


def test_create_rejects_blank_description(client):
    res = add(client, description="   ")
    assert res.status_code == 400


def test_create_rejects_non_json_body(client):
    res = client.post("/expenses", data="not json", content_type="text/plain")
    assert res.status_code == 400


def test_sql_injection_text_is_stored_as_plain_text(client):
    evil = "x'); DROP TABLE expenses; --"
    res = add(client, description=evil)
    assert res.status_code == 201
    # the table still exists and the text was saved exactly as sent
    assert client.get("/expenses").get_json()[0]["description"] == evil


# ---------- READ ----------

def test_list_is_empty_at_start(client):
    assert client.get("/expenses").get_json() == []


def test_list_filters_by_category_case_insensitive(client):
    add(client, category="Food")
    add(client, category="Travel", description="Taxi")
    res = client.get("/expenses?category=FOOD")
    data = res.get_json()
    assert len(data) == 1
    assert data[0]["category"] == "food"


def test_get_one_and_missing_id(client):
    add(client)
    assert client.get("/expenses/1").status_code == 200
    assert client.get("/expenses/99").status_code == 404


def test_summary_totals_per_category(client):
    add(client, amount=100.5, category="food")
    add(client, amount=49.5, category="food")
    add(client, amount=30, category="travel")
    data = client.get("/expenses/summary").get_json()
    assert data["by_category"] == {"food": 150.0, "travel": 30.0}
    assert data["total"] == 180.0


# ---------- UPDATE ----------

def test_update_changes_only_sent_fields(client):
    add(client)
    res = client.put("/expenses/1", json={"amount": 200})
    assert res.status_code == 200
    data = res.get_json()
    assert data["amount"] == 200.0
    assert data["description"] == "Lunch"  # unchanged


def test_update_with_invalid_value_returns_400(client):
    add(client)
    assert client.put("/expenses/1", json={"amount": -1}).status_code == 400


def test_update_with_empty_body_returns_400(client):
    add(client)
    assert client.put("/expenses/1", json={}).status_code == 400


def test_update_missing_id_returns_404(client):
    assert client.put("/expenses/42", json={"amount": 10}).status_code == 404


# ---------- DELETE ----------

def test_delete_removes_expense(client):
    add(client)
    assert client.delete("/expenses/1").status_code == 204
    assert client.get("/expenses/1").status_code == 404


def test_delete_missing_id_returns_404(client):
    assert client.delete("/expenses/7").status_code == 404
