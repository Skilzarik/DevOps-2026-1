"""Продажи и бизнес-правило контроля остатков (ТЗ 4.3b, 6.3, 6.4)."""

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.integration


def _sell(client, headers, disc_id, quantity):
    return client.post("/sales/", json={"disc_id": disc_id, "quantity": quantity}, headers=headers)


def _stock(client, headers) -> int:
    return client.get("/discs/", headers=headers).json()[0]["stock"]


def test_sale_decreases_stock_and_records_total(client, admin_headers, disc):
    resp = _sell(client, admin_headers, disc["id"], 2)
    assert resp.status_code == 201
    body = resp.json()
    assert body["quantity"] == 2
    assert body["total_price"] == pytest.approx(20.0)
    assert _stock(client, admin_headers) == 3


def test_total_price_uses_current_unit_price(client, admin_headers, musician):
    created = client.post(
        "/discs/",
        json={"title": "Cheap", "musician_id": musician["id"], "price": 19.99, "stock": 10},
        headers=admin_headers,
    ).json()
    resp = _sell(client, admin_headers, created["id"], 3)
    assert resp.json()["total_price"] == pytest.approx(59.97)


def test_seller_can_register_sale(client, seller_headers, disc):
    resp = _sell(client, seller_headers, disc["id"], 1)
    assert resp.status_code == 201
    me = client.get("/auth/me", headers=seller_headers).json()
    assert resp.json()["seller_id"] == me["id"]


def test_sale_of_entire_stock_is_allowed(client, admin_headers, disc):
    resp = _sell(client, admin_headers, disc["id"], disc["stock"])
    assert resp.status_code == 201
    assert _stock(client, admin_headers) == 0


def test_sale_exceeding_stock_is_rejected_and_stock_unchanged(client, admin_headers, disc, db):
    resp = _sell(client, admin_headers, disc["id"], disc["stock"] + 1)
    assert resp.status_code == 400
    assert "Not enough stock" in resp.json()["detail"]
    assert _stock(client, admin_headers) == disc["stock"]
    assert db.execute(text("SELECT count(*) FROM sales")).scalar_one() == 0


def test_sale_of_out_of_stock_disc_rejected(client, admin_headers, musician):
    empty = client.post(
        "/discs/",
        json={"title": "Empty", "musician_id": musician["id"], "price": 5, "stock": 0},
        headers=admin_headers,
    ).json()
    assert _sell(client, admin_headers, empty["id"], 1).status_code == 400


@pytest.mark.parametrize("quantity", [0, -1])
def test_sale_quantity_must_be_positive(client, admin_headers, disc, quantity):
    assert _sell(client, admin_headers, disc["id"], quantity).status_code == 422
    assert _stock(client, admin_headers) == disc["stock"]


def test_sale_quantity_must_be_integer(client, admin_headers, disc):
    resp = client.post(
        "/sales/", json={"disc_id": disc["id"], "quantity": "many"}, headers=admin_headers
    )
    assert resp.status_code == 422


def test_sale_of_unknown_disc_returns_404(client, admin_headers):
    assert _sell(client, admin_headers, 999, 1).status_code == 404


def test_sale_requires_token(client, disc):
    resp = client.post("/sales/", json={"disc_id": disc["id"], "quantity": 1})
    assert resp.status_code in (401, 403)


def test_consecutive_sales_accumulate(client, admin_headers, disc):
    assert _sell(client, admin_headers, disc["id"], 2).status_code == 201
    assert _sell(client, admin_headers, disc["id"], 2).status_code == 201
    assert _stock(client, admin_headers) == 1
    # Третья продажа превышает остаток (1) и отклоняется.
    assert _sell(client, admin_headers, disc["id"], 2).status_code == 400
    assert _stock(client, admin_headers) == 1


def test_sales_list_is_newest_first(client, admin_headers, disc):
    first = _sell(client, admin_headers, disc["id"], 1).json()["id"]
    second = _sell(client, admin_headers, disc["id"], 1).json()["id"]
    listing = client.get("/sales/", headers=admin_headers).json()
    assert [s["id"] for s in listing] == [second, first]


def test_sales_list_requires_token(client):
    assert client.get("/sales/").status_code in (401, 403)
