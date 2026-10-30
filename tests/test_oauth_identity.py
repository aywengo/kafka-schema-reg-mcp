"""Fixture-issuer tests for the single resource-server verifier."""

from __future__ import annotations

import base64
import logging
import time

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from joserfc import jwt
from joserfc.jwk import OKPKey, RSAKey
from joserfc.jws import JWSRegistry

from oauth_provider import (
    ENTERPRISE_MANAGED_AUTHORIZATION,
    JWT_BEARER_GRANT,
    AuthenticationError,
    FakeAuthorizationServer,
    OAuth21BearerAuthProvider,
    advertised_grants,
    authenticate,
    protected_resource_grant_metadata,
)

ISSUER = "https://issuer.example.test"
KID = "ed-1"


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _signing_material() -> tuple[OKPKey, dict]:
    private = Ed25519PrivateKey.generate()
    raw_private = private.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    raw_public = private.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    public_jwk = {"kty": "OKP", "crv": "Ed25519", "x": _b64url(raw_public), "kid": KID}
    signing_key = OKPKey.import_key({**public_jwk, "d": _b64url(raw_private)})
    return signing_key, {"keys": [public_jwk]}


def _server(grant_types: list[str]) -> tuple[FakeAuthorizationServer, OKPKey]:
    signing_key, jwks = _signing_material()
    server = FakeAuthorizationServer(
        metadata={
            "issuer": ISSUER,
            "authorization_endpoint": f"{ISSUER}/authorize",
            "token_endpoint": f"{ISSUER}/token",
            "jwks_uri": f"{ISSUER}/jwks",
            "grant_types_supported": grant_types,
        },
        jwks=jwks,
    )
    return server, signing_key


def _token(signing_key: OKPKey, **claims: object) -> str:
    now = int(time.time())
    payload: dict[str, object] = {"iss": ISSUER, "iat": now, "exp": now + 3600}
    payload.update(claims)
    registry = JWSRegistry(algorithms=["EdDSA"])
    encoded = jwt.encode({"alg": "EdDSA", "kid": KID}, payload, signing_key, registry=registry)
    if isinstance(encoded, bytes):
        return encoded.decode("ascii")
    return encoded


async def test_authorization_code_expands_admin_scope() -> None:
    server, signing_key = _server(["authorization_code", "client_credentials", JWT_BEARER_GRANT])
    token = _token(signing_key, gty="authorization_code", sub="user", scope="admin")
    principal = await authenticate(token, authorization_server=server)
    assert principal.subject == "user"
    assert principal.scopes == frozenset({"admin", "write", "read"})


async def test_authorization_code_without_sub_is_rejected() -> None:
    server, signing_key = _server(["authorization_code"])
    token = _token(signing_key, gty="authorization_code", azp="client", scope="admin")
    with pytest.raises(AuthenticationError):
        await authenticate(token, authorization_server=server)


async def test_client_credentials_without_user_sub() -> None:
    server, signing_key = _server(["client_credentials"])
    token = _token(signing_key, gty="client_credentials", client_id="svc", scope="write")
    principal = await authenticate(token, authorization_server=server)
    assert principal.subject is None
    assert principal.client_id == "svc"
    assert principal.scopes == frozenset({"write", "read"})


async def test_jwt_bearer_with_sub() -> None:
    server, signing_key = _server([JWT_BEARER_GRANT])
    token = _token(signing_key, gty=JWT_BEARER_GRANT, sub="user", scope="read")
    principal = await authenticate(token, authorization_server=server)
    assert principal.subject == "user"
    assert principal.client_id is None


async def test_missing_gty_accepts_azp_without_sub() -> None:
    server, signing_key = _server(["authorization_code", "client_credentials"])
    token = _token(signing_key, azp="client", scope="read")
    principal = await authenticate(token, authorization_server=server)
    assert principal.subject is None
    assert principal.client_id == "client"
    assert principal.scopes == frozenset({"read"})


async def test_metadata_omits_extension_when_issuer_omits_jwt_bearer() -> None:
    server, _signing_key = _server(["authorization_code", "client_credentials"])
    grants = await advertised_grants(authorization_server=server)
    assert grants == ("authorization_code", "client_credentials")
    metadata = protected_resource_grant_metadata(grants)
    assert ENTERPRISE_MANAGED_AUTHORIZATION not in metadata.get("extensions", {})
    assert "extensions" not in metadata


async def test_metadata_advertises_extension_when_issuer_lists_jwt_bearer() -> None:
    server, _signing_key = _server(["authorization_code", JWT_BEARER_GRANT, "refresh_token"])
    grants = await advertised_grants(authorization_server=server)
    assert grants == ("authorization_code", JWT_BEARER_GRANT)
    metadata = protected_resource_grant_metadata(grants)
    assert metadata["extensions"][ENTERPRISE_MANAGED_AUTHORIZATION] == {}


async def test_authenticate_rejects_a_resource_the_token_does_not_name() -> None:
    server, signing_key = _server(["authorization_code"])
    token = _token(signing_key, gty="authorization_code", sub="user", scope="read", aud="https://other.example")
    with pytest.raises(AuthenticationError):
        await authenticate(token, authorization_server=server, resource="https://mcp.example.test")


async def test_authenticate_accepts_the_resource_claim() -> None:
    server, signing_key = _server(["authorization_code"])
    token = _token(
        signing_key,
        gty="authorization_code",
        sub="user",
        scope="read",
        resource="https://mcp.example.test",
    )
    principal = await authenticate(token, authorization_server=server, resource="https://mcp.example.test")
    assert principal.subject == "user"


async def test_load_access_token_requires_a_configured_resource_indicator() -> None:
    server, signing_key = _server(["authorization_code"])
    provider = OAuth21BearerAuthProvider(
        authorization_server=server,
        resource_indicators=["https://mcp.example.test"],
    )
    missing = _token(signing_key, gty="authorization_code", sub="user", scope="read")
    assert await provider.load_access_token(missing) is None
    present = _token(
        signing_key,
        gty="authorization_code",
        sub="user",
        scope="read",
        aud="https://mcp.example.test",
    )
    assert await provider.load_access_token(present) is not None


def _rsa_pair() -> tuple[RSAKey, dict]:
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = private.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    signing_key = RSAKey.import_key(pem)
    public = signing_key.as_dict(private=False)
    public.pop("alg", None)
    public.pop("kid", None)
    return signing_key, public


def _rsa_token(signing_key: RSAKey, **claims: object) -> str:
    now = int(time.time())
    payload: dict[str, object] = {"iss": ISSUER, "iat": now, "exp": now + 3600, "gty": "client_credentials"}
    payload.update(claims)
    registry = JWSRegistry(algorithms=["RS256"])
    encoded = jwt.encode({"alg": "RS256"}, payload, signing_key, registry=registry)
    if isinstance(encoded, bytes):
        return encoded.decode("ascii")
    return encoded


async def test_rsa_key_without_alg_verifies_rs256() -> None:
    signing_key, public = _rsa_pair()
    server = FakeAuthorizationServer(
        metadata={"issuer": ISSUER, "grant_types_supported": ["client_credentials"]},
        jwks={"keys": [public]},
    )
    token = _rsa_token(signing_key, client_id="svc", scope="read")
    principal = await authenticate(token, authorization_server=server)
    assert principal.client_id == "svc"
    assert principal.scopes == frozenset({"read"})


async def test_missing_kid_tries_each_compatible_key() -> None:
    signing_key, public = _rsa_pair()
    _other, decoy = _rsa_pair()
    server = FakeAuthorizationServer(
        metadata={"issuer": ISSUER, "grant_types_supported": ["client_credentials"]},
        jwks={"keys": [decoy, public]},
    )
    token = _rsa_token(signing_key, client_id="svc", scope="read")
    principal = await authenticate(token, authorization_server=server)
    assert principal.client_id == "svc"


async def test_jwks_document_is_reused_for_the_cache_ttl() -> None:
    server, signing_key = _server(["client_credentials"])
    calls = {"n": 0}
    original = server.jwks

    async def counting() -> dict:
        calls["n"] += 1
        return await original()

    server.jwks = counting  # type: ignore[method-assign]
    provider = OAuth21BearerAuthProvider(authorization_server=server)
    token = _token(signing_key, gty="client_credentials", client_id="svc", scope="read")
    assert await provider.load_access_token(token) is not None
    assert await provider.load_access_token(token) is not None
    assert calls["n"] == 1


async def test_authorization_code_without_s256_warns_and_keeps_the_grant(caplog: pytest.LogCaptureFixture) -> None:
    server, _signing_key = _server(["authorization_code"])
    with caplog.at_level(logging.WARNING):
        grants = await advertised_grants(authorization_server=server)
    assert grants == ("authorization_code",)
    assert "S256" in caplog.text


async def test_authorization_code_with_s256_does_not_warn(caplog: pytest.LogCaptureFixture) -> None:
    server = FakeAuthorizationServer(
        metadata={
            "issuer": ISSUER,
            "grant_types_supported": ["authorization_code"],
            "code_challenge_methods_supported": ["S256"],
        },
        jwks={"keys": []},
    )
    with caplog.at_level(logging.WARNING):
        grants = await advertised_grants(authorization_server=server)
    assert grants == ("authorization_code",)
    assert "without PKCE S256" not in caplog.text
