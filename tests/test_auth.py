import pytest
from fastapi import HTTPException, Request
from api.auth import verify_id_token, get_current_user


@pytest.mark.asyncio
async def test_verify_token_valid(monkeypatch):
    def fake_verify(token):
        assert token == 'abc'
        return {'uid': 'u1'}

    monkeypatch.setattr('api.auth.auth.verify_id_token', fake_verify)
    payload = await verify_id_token('abc')
    assert payload['uid'] == 'u1'


@pytest.mark.asyncio
async def test_verify_token_invalid(monkeypatch):
    def fake_verify(token):
        raise ValueError('bad')

    monkeypatch.setattr('api.auth.auth.verify_id_token', fake_verify)
    with pytest.raises(HTTPException):
        await verify_id_token('bad')


@pytest.mark.asyncio
async def test_get_current_user(monkeypatch):
    def fake_verify(token):
        return {'uid': 'u2'}

    monkeypatch.setattr('api.auth.auth.verify_id_token', fake_verify)
    scope = {
        'type': 'http',
        'headers': [(b'authorization', b'Bearer abc')],
        'method': 'GET',
        'path': '/',
    }
    req = Request(scope)
    user = await get_current_user(req)
    assert user['uid'] == 'u2'

    req2 = Request({'type': 'http', 'headers': [], 'method': 'GET', 'path': '/'})
    assert await get_current_user(req2) is None
