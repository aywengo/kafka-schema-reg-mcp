"""VIEWONLY enforcement at the HTTP boundary."""

import pytest

import schema_registry_common as src


def session(url="http://registry.example/base", viewonly=True):
    return src.GuardedSession(src.RegistryConfig(name="prod", url=url, viewonly=viewonly))


def test_allowlisted_read_posts():
    s = session()
    assert s._is_read_post("http://registry.example/base/subjects/orders")
    assert s._is_read_post("http://registry.example/base/compatibility/subjects/orders/versions/latest")
    assert s._is_read_post("http://registry.example/base/contexts/prod/subjects/orders")
    assert s._is_read_post("http://registry.example/base/contexts/prod/compatibility/subjects/orders/versions/3")


def test_mutating_posts_are_not_allowlisted():
    s = session()
    assert not s._is_read_post("http://registry.example/base/subjects/orders/versions")
    assert not s._is_read_post("http://registry.example/base/contexts/prod/subjects/orders/versions")
    assert not s._is_read_post("http://registry.example/base/config")


def test_viewonly_rejects_put_and_delete():
    s = session()
    with pytest.raises(src.ViewOnlyError):
        s.put("http://registry.example/base/config", json={})
    with pytest.raises(src.ViewOnlyError):
        s.delete("http://registry.example/base/subjects/orders")


def test_viewonly_rejects_mutating_post():
    s = session()
    with pytest.raises(src.ViewOnlyError):
        s.post("http://registry.example/base/subjects/orders/versions", json={})


def test_writable_registry_is_not_guarded():
    s = session(viewonly=False)
    s._guard("POST", "http://registry.example/base/subjects/orders/versions")
    s._guard("PUT", "http://registry.example/base/config")
