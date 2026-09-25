"""Tokens are verified against the project's public keys (JWKS), as Supabase issues them."""

import json
import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import HTTPException

from drishti.auth import verify_token


def _keypair(kid):
    private = ec.generate_private_key(ec.SECP256R1())
    jwk = json.loads(jwt.algorithms.ECAlgorithm.to_jwk(private.public_key()))
    jwk.update({"kid": kid, "alg": "ES256", "use": "sig"})
    return private, jwk


def _token(private, kid, **claims):
    body = {"sub": "user-1", "aud": "authenticated", "exp": int(time.time()) + 600, **claims}
    return jwt.encode(body, private, algorithm="ES256", headers={"kid": kid})


@pytest.fixture()
def keys():
    private, jwk = _keypair("k1")
    return private, jwt.PyJWKSet.from_dict({"keys": [jwk]})


def test_a_valid_token_is_accepted(keys):
    private, jwks = keys
    assert verify_token(_token(private, "k1"), jwks)["sub"] == "user-1"


def test_a_token_signed_by_another_key_is_refused(keys):
    _, jwks = keys
    other, _ = _keypair("k1")
    with pytest.raises(HTTPException) as e:
        verify_token(_token(other, "k1"), jwks)
    assert e.value.status_code == 401


def test_an_expired_token_is_refused(keys):
    private, jwks = keys
    with pytest.raises(HTTPException):
        verify_token(_token(private, "k1", exp=int(time.time()) - 5), jwks)


def test_an_unknown_key_id_is_refused(keys):
    private, jwks = keys
    with pytest.raises(HTTPException):
        verify_token(_token(private, "nope"), jwks)
