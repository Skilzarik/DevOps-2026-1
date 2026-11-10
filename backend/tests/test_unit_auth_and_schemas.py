"""Unit-тесты логики без базы данных: пароли, JWT, роли, валидация схем."""

import time
from datetime import timedelta

import pytest
from fastapi import HTTPException
from jose import JWTError, jwt
from jose.exceptions import ExpiredSignatureError
from pydantic import ValidationError

from app import auth, models, schemas
from app.database import settings

pytestmark = pytest.mark.unit


# --- пароли ---------------------------------------------------------------


def test_password_hash_is_not_plaintext():
    hashed = auth.get_password_hash("S3cret-pass")
    assert hashed != "S3cret-pass"
    assert hashed.startswith("$2")


def test_password_verification():
    hashed = auth.get_password_hash("S3cret-pass")
    assert auth.verify_password("S3cret-pass", hashed) is True
    assert auth.verify_password("wrong-pass", hashed) is False


def test_same_password_gives_different_hashes():
    assert auth.get_password_hash("same") != auth.get_password_hash("same")


# --- JWT ------------------------------------------------------------------


def _decode(token: str) -> dict:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])


def test_token_contains_subject_and_expiry():
    payload = _decode(auth.create_access_token({"sub": "alice"}))
    remaining = payload["exp"] - time.time()
    assert payload["sub"] == "alice"
    assert 0 < remaining <= settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60 + 5


def test_custom_expiry_is_respected():
    payload = _decode(auth.create_access_token({"sub": "alice"}, timedelta(minutes=5)))
    assert 280 < payload["exp"] - time.time() <= 305


def test_expired_token_is_rejected():
    token = auth.create_access_token({"sub": "alice"}, timedelta(seconds=-1))
    with pytest.raises(ExpiredSignatureError):
        _decode(token)


def test_token_signed_with_other_key_is_rejected():
    token = auth.create_access_token({"sub": "alice"})
    with pytest.raises(JWTError):
        jwt.decode(token, "another-key", algorithms=[settings.ALGORITHM])


# --- роли -----------------------------------------------------------------


def test_require_admin_rejects_seller():
    seller = models.User(username="s", hashed_password="x", role="seller")
    with pytest.raises(HTTPException) as exc:
        auth.require_admin(seller)
    assert exc.value.status_code == 403


def test_require_admin_accepts_admin():
    admin = models.User(username="a", hashed_password="x", role="admin")
    assert auth.require_admin(admin) is admin


# --- валидация схем (ошибочные данные и граничные случаи) -----------------


@pytest.mark.parametrize("price", [0, -1, -0.01])
def test_disc_price_must_be_positive(price):
    with pytest.raises(ValidationError):
        schemas.DiscCreate(title="d", musician_id=1, price=price, stock=1)


def test_disc_smallest_positive_price_is_valid():
    assert schemas.DiscCreate(title="d", musician_id=1, price=0.01, stock=1).price == 0.01


def test_disc_negative_stock_is_invalid():
    with pytest.raises(ValidationError):
        schemas.DiscCreate(title="d", musician_id=1, price=1, stock=-1)


def test_disc_zero_stock_is_valid():
    assert schemas.DiscCreate(title="d", musician_id=1, price=1, stock=0).stock == 0


@pytest.mark.parametrize("quantity", [0, -3])
def test_sale_quantity_must_be_positive(quantity):
    with pytest.raises(ValidationError):
        schemas.SaleCreate(disc_id=1, quantity=quantity)


def test_sale_quantity_one_is_valid():
    assert schemas.SaleCreate(disc_id=1, quantity=1).quantity == 1


def test_user_role_defaults_to_seller():
    assert schemas.UserCreate(username="u", password="p").role == "seller"


def test_unknown_user_role_is_rejected():
    with pytest.raises(ValidationError):
        schemas.UserCreate(username="u", password="p", role="root")
