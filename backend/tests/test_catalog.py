"""Каталог: музыканты и диски, разграничение прав, целостность (ТЗ 3.2, 4.2, 6.4)."""

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.integration


def _count(db, table: str) -> int:
    # Имя таблицы задаётся только самими тестами, пользовательского ввода здесь нет.
    return db.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()


def _sell(client, headers, disc_id, quantity):
    return client.post("/sales/", json={"disc_id": disc_id, "quantity": quantity}, headers=headers)


# --- музыканты -------------------------------------------------------------


def test_admin_creates_musician(client, admin_headers):
    resp = client.post("/musicians/", json={"name": "Muse", "genre": "Rock"}, headers=admin_headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Muse"
    assert body["genre"] == "Rock"
    assert body["created_by"] is not None


def test_seller_cannot_create_musician(client, seller_headers):
    resp = client.post(
        "/musicians/", json={"name": "Muse", "genre": "Rock"}, headers=seller_headers
    )
    assert resp.status_code == 403


def test_musician_requires_genre(client, admin_headers):
    resp = client.post("/musicians/", json={"name": "NoGenre"}, headers=admin_headers)
    assert resp.status_code == 422


def test_musicians_list_requires_token(client):
    assert client.get("/musicians/").status_code in (401, 403)


def test_seller_sees_musicians(client, seller_headers, musician):
    resp = client.get("/musicians/", headers=seller_headers)
    assert resp.status_code == 200
    assert [m["name"] for m in resp.json()] == ["Muse"]


def test_admin_deletes_musician_without_discs(client, admin_headers, musician):
    assert client.delete(f"/musicians/{musician['id']}", headers=admin_headers).status_code == 204
    assert client.get("/musicians/", headers=admin_headers).json() == []


def test_seller_cannot_delete_musician(client, seller_headers, musician):
    assert client.delete(f"/musicians/{musician['id']}", headers=seller_headers).status_code == 403
    assert len(client.get("/musicians/", headers=seller_headers).json()) == 1


def test_delete_unknown_musician_returns_404(client, admin_headers):
    assert client.delete("/musicians/999", headers=admin_headers).status_code == 404


def test_musician_with_sold_discs_cannot_be_deleted(client, admin_headers, musician, disc, db):
    assert _sell(client, admin_headers, disc["id"], 1).status_code == 201
    resp = client.delete(f"/musicians/{musician['id']}", headers=admin_headers)
    assert resp.status_code == 400
    assert _count(db, "sales") == 1
    assert _count(db, "discs") == 1


def test_deleting_musician_removes_unsold_discs(client, admin_headers, musician, disc, db):
    assert client.delete(f"/musicians/{musician['id']}", headers=admin_headers).status_code == 204
    assert _count(db, "discs") == 0


# --- диски -----------------------------------------------------------------


def test_admin_creates_disc(client, admin_headers, musician):
    resp = client.post(
        "/discs/",
        json={"title": "Absolution", "musician_id": musician["id"], "price": 10.5, "stock": 3},
        headers=admin_headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["title"] == "Absolution"
    assert body["price"] == 10.5
    assert body["stock"] == 3
    assert body["musician_id"] == musician["id"]


def test_disc_with_unknown_musician_rejected(client, admin_headers):
    resp = client.post(
        "/discs/",
        json={"title": "Ghost", "musician_id": 999, "price": 1, "stock": 1},
        headers=admin_headers,
    )
    assert resp.status_code == 400
    assert "Musician not found" in resp.json()["detail"]


@pytest.mark.parametrize("price", [0, -5])
def test_disc_price_must_be_positive_api(client, admin_headers, musician, price):
    resp = client.post(
        "/discs/",
        json={"title": "Bad", "musician_id": musician["id"], "price": price, "stock": 1},
        headers=admin_headers,
    )
    assert resp.status_code == 422


def test_disc_negative_stock_rejected(client, admin_headers, musician):
    resp = client.post(
        "/discs/",
        json={"title": "Bad", "musician_id": musician["id"], "price": 5, "stock": -1},
        headers=admin_headers,
    )
    assert resp.status_code == 422


def test_disc_zero_stock_allowed(client, admin_headers, musician):
    resp = client.post(
        "/discs/",
        json={"title": "Empty", "musician_id": musician["id"], "price": 5, "stock": 0},
        headers=admin_headers,
    )
    assert resp.status_code == 201


def test_seller_cannot_create_disc(client, seller_headers, musician):
    resp = client.post(
        "/discs/",
        json={"title": "X", "musician_id": musician["id"], "price": 5, "stock": 1},
        headers=seller_headers,
    )
    assert resp.status_code == 403


def test_seller_sees_discs(client, seller_headers, disc):
    resp = client.get("/discs/", headers=seller_headers)
    assert resp.status_code == 200
    assert [d["title"] for d in resp.json()] == ["Absolution"]


def test_discs_list_requires_token(client):
    assert client.get("/discs/").status_code in (401, 403)


# --- пополнение остатка -----------------------------------------------------


def test_restock_increases_stock(client, admin_headers, disc):
    resp = client.post(f"/discs/{disc['id']}/restock", json={"quantity": 3}, headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["stock"] == disc["stock"] + 3


@pytest.mark.parametrize("quantity", [0, -1])
def test_restock_requires_positive_quantity(client, admin_headers, disc, quantity):
    resp = client.post(
        f"/discs/{disc['id']}/restock", json={"quantity": quantity}, headers=admin_headers
    )
    assert resp.status_code == 400
    stock = client.get("/discs/", headers=admin_headers).json()[0]["stock"]
    assert stock == disc["stock"]


def test_restock_unknown_disc_returns_404(client, admin_headers):
    resp = client.post("/discs/999/restock", json={"quantity": 1}, headers=admin_headers)
    assert resp.status_code == 404


def test_seller_cannot_restock(client, seller_headers, disc):
    resp = client.post(f"/discs/{disc['id']}/restock", json={"quantity": 1}, headers=seller_headers)
    assert resp.status_code == 403


# --- удаление дисков --------------------------------------------------------


def test_admin_deletes_disc_without_sales(client, admin_headers, disc):
    assert client.delete(f"/discs/{disc['id']}", headers=admin_headers).status_code == 204
    assert client.get("/discs/", headers=admin_headers).json() == []


def test_disc_with_sales_cannot_be_deleted(client, admin_headers, disc, db):
    assert _sell(client, admin_headers, disc["id"], 1).status_code == 201
    resp = client.delete(f"/discs/{disc['id']}", headers=admin_headers)
    assert resp.status_code == 400
    assert "existing sales" in resp.json()["detail"]
    assert _count(db, "discs") == 1
    assert _count(db, "sales") == 1


def test_delete_unknown_disc_returns_404(client, admin_headers):
    assert client.delete("/discs/999", headers=admin_headers).status_code == 404


def test_seller_cannot_delete_disc(client, seller_headers, disc):
    assert client.delete(f"/discs/{disc['id']}", headers=seller_headers).status_code == 403
    assert len(client.get("/discs/", headers=seller_headers).json()) == 1
