import pytest
from sanic import Sanic, Request
from sanic.response import json
from sanic_testing.testing import SanicASGITestClient
from jose import jwt

from api import authorized, LoginApplyType, AuthorizedUser, TokenPayload
from api.authorization import _LoginResponse, _RefreshTokenResponse, _decode_token
from utils.Settings import ConfigHandler

from test import test_client, app

_login_params = {
    'apiKey': ConfigHandler().get_config('ApiKey', 'WX_Mini_APP'), 'applyType': 'WX_Mini_APP',
    'username': "test2", "password": "123"
}


@pytest.mark.asyncio
async def test_authorize(test_client: SanicASGITestClient):
    request1, response1 = await test_client.post(
        "/v1/authorization/login",
        json={'apiKey': ConfigHandler().get_config('ApiKey', 'IOS_APP'), 'applyType': 'WX_Mini_APP',
              'username': "test2", "password": "123"}
    )
    assert response1.status == 401

    request2, response2 = await test_client.post(
        "/v1/authorization/login",
        json=_login_params
    )
    assert response2.status == 200

    res = _LoginResponse.parse_obj(response2.json['data'])
    token_data: TokenPayload = TokenPayload.parse_obj(_decode_token(res.token))
    assert token_data.timestamp == res.tokenExpireTime
    assert token_data.applyType == 'WX_Mini_APP'
    assert token_data.username == 'test2'
    assert token_data.password == '123'

    refresh_token_data: TokenPayload = TokenPayload.parse_obj(_decode_token(res.refreshToken))
    assert refresh_token_data.timestamp == res.refreshTokenExpireTime
    assert refresh_token_data.applyType == 'WX_Mini_APP'
    assert refresh_token_data.username == 'test2'
    assert refresh_token_data.password == '123'


async def get_success_login_response(test_client: SanicASGITestClient, without_user: bool = False) -> _LoginResponse:
    param = _login_params.copy()
    if without_user:
        param.pop('username')
        param.pop('password')
    request, response = await test_client.post(
        "/v1/authorization/login",
        json=param
    )
    assert response.status == 200

    return _LoginResponse.parse_obj(response.json['data'])


@pytest.mark.asyncio
async def test_refresh_token(test_client: SanicASGITestClient):
    success_login_response = await get_success_login_response(test_client)

    request, response = await test_client.post(
        "/v1/authorization/refreshToken",
        json={'refreshToken': success_login_response.refreshToken}
    )
    assert response.status == 200

    res = _RefreshTokenResponse.parse_obj(response.json['data'])
    token_data: TokenPayload = TokenPayload.parse_obj(_decode_token(res.token))
    assert token_data.timestamp == res.tokenExpireTime
    assert token_data.applyType == 'WX_Mini_APP'
    assert token_data.username == 'test2'
    assert token_data.password == '123'


@pytest.mark.asyncio
async def test_authorized_include(app: Sanic):
    @app.post('test1')
    @authorized(include=[LoginApplyType.WX_Mini_APP], need_user=True)
    def test1(request: Request, user: AuthorizedUser):
        return json(user.dict())

    test_client = SanicASGITestClient(app)

    success_login_response = await get_success_login_response(test_client)

    request, response = await test_client.post(
        "/test1",
        json=_login_params,
        headers={'Authorization': 'Bearer ' + success_login_response.token}
    )
    assert response.status == 200
    assert response.json['username'] == 'test2'


@pytest.mark.asyncio
async def test_authorized_exclude(app: Sanic):
    @app.post('test1')
    @authorized(exclude=[LoginApplyType.WX_Mini_APP])
    def test1(request: Request, user: AuthorizedUser):
        return json(user.dict())

    test_client = SanicASGITestClient(app)

    success_login_response = await get_success_login_response(test_client)

    request, response = await test_client.post(
        "/test1",
        json=_login_params,
        headers={'Authorization': 'Bearer ' + success_login_response.token}
    )
    assert response.status == 401


@pytest.mark.asyncio
async def test_when_no_user(app: Sanic):
    @app.post('test1')
    @authorized(include=[LoginApplyType.WX_Mini_APP], need_user=True)
    def test1(request: Request, user: AuthorizedUser):
        return json(user.dict())

    test_client = SanicASGITestClient(app)

    success_login_response = await get_success_login_response(test_client, without_user=True)

    request, response = await test_client.post(
        "/test1",
        json=_login_params,
        headers={'Authorization': 'Bearer ' + success_login_response.token}
    )
    assert response.status == 401
