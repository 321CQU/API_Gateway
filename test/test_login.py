import pytest
from sanic import Sanic, Request
from sanic.response import json
from sanic_testing.testing import SanicASGITestClient

from api import authorized, LoginApplyType, AuthorizedUser, TokenPayload
from api.authorization import (
    _LoginResponse,
    _RefreshTokenResponse,
    _TEMPORARY_LOGIN_ERROR_INFO,
    _TEMPORARY_LOGIN_PASSWORD,
    _TEMPORARY_LOGIN_USERNAME,
    _decode_token,
)
from test import test_client, app
from utils.Settings import ConfigManager

_login_params = {
    'apiKey': ConfigManager().get_config('ApiKey', 'WX_Mini_APP'), 'applyType': 'WX_Mini_APP',
    'username': "test2", "password": "123"
}


@pytest.mark.asyncio
async def test_authorize(test_client: SanicASGITestClient):
    request1, response1 = await test_client.post(
        "/v1/authorization/login",
        json={'apiKey': ConfigManager().get_config('ApiKey', 'IOS_APP'), 'applyType': 'WX_Mini_APP',
              'username': "test2", "password": "123"}
    )
    assert response1.status == 401

    request2, response2 = await test_client.post(
        "/v1/authorization/login",
        json=_login_params
    )
    assert response2.status == 200

    res = _LoginResponse.model_validate(response2.json['data'])
    token_data: TokenPayload = TokenPayload.parse_obj(_decode_token(res.token))
    assert token_data.timestamp == res.tokenExpireTime
    assert token_data.applyType == 'WX_Mini_APP'
    assert token_data.username == _TEMPORARY_LOGIN_USERNAME
    assert token_data.password == _TEMPORARY_LOGIN_PASSWORD

    refresh_token_data: TokenPayload = TokenPayload.parse_obj(_decode_token(res.refreshToken))
    assert refresh_token_data.timestamp == res.refreshTokenExpireTime
    assert refresh_token_data.applyType == 'WX_Mini_APP'
    assert refresh_token_data.username == _TEMPORARY_LOGIN_USERNAME
    assert refresh_token_data.password == _TEMPORARY_LOGIN_PASSWORD


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

    return _LoginResponse.model_validate(response.json['data'])


@pytest.mark.asyncio
async def test_refresh_token(test_client: SanicASGITestClient):
    success_login_response = await get_success_login_response(test_client)

    request, response = await test_client.post(
        "/v1/authorization/refreshToken",
        json={'refreshToken': success_login_response.refreshToken}
    )
    assert response.status == 200

    res = _RefreshTokenResponse.model_validate(response.json['data'])
    token_data: TokenPayload = TokenPayload.parse_obj(_decode_token(res.token))
    assert token_data.timestamp == res.tokenExpireTime
    assert token_data.applyType == 'WX_Mini_APP'
    assert token_data.username == _TEMPORARY_LOGIN_USERNAME
    assert token_data.password == _TEMPORARY_LOGIN_PASSWORD


@pytest.mark.asyncio
async def test_authorized_include(app: Sanic):
    @app.post('test_authorized_include')
    @authorized(include=[LoginApplyType.WX_Mini_APP], need_user=True)
    def test_authorized_include_handler(request: Request, user: AuthorizedUser):
        return json(user.model_dump())

    test_client = SanicASGITestClient(app)

    success_login_response = await get_success_login_response(test_client)

    request, response = await test_client.post(
        "/test_authorized_include",
        json=_login_params,
        headers={'Authorization': 'Bearer ' + success_login_response.token}
    )
    assert response.status == 200
    assert response.json['status'] == 0
    assert response.json['msg'] == _TEMPORARY_LOGIN_ERROR_INFO


@pytest.mark.asyncio
async def test_authorized_rejects_temporary_login_user(app: Sanic):
    @app.post('test_temporary_login_user')
    @authorized()
    def test_temporary_login_user(request: Request):
        return json({'ok': True})

    test_client = SanicASGITestClient(app)

    success_login_response = await get_success_login_response(test_client)

    request, response = await test_client.post(
        "/test_temporary_login_user",
        json=_login_params,
        headers={'Authorization': 'Bearer ' + success_login_response.token}
    )
    assert response.status == 200
    assert response.json['status'] == 0
    assert response.json['msg'] == _TEMPORARY_LOGIN_ERROR_INFO


@pytest.mark.asyncio
async def test_authorized_exclude(app: Sanic):
    @app.post('test_authorized_exclude')
    @authorized(exclude=[LoginApplyType.WX_Mini_APP])
    def test_authorized_exclude_handler(request: Request, user: AuthorizedUser):
        return json(user.model_dump())

    test_client = SanicASGITestClient(app)

    success_login_response = await get_success_login_response(test_client)

    request, response = await test_client.post(
        "/test_authorized_exclude",
        json=_login_params,
        headers={'Authorization': 'Bearer ' + success_login_response.token}
    )
    assert response.status == 403


@pytest.mark.asyncio
async def test_when_no_user(app: Sanic):
    @app.post('test_when_no_user')
    @authorized(include=[LoginApplyType.WX_Mini_APP], need_user=True)
    def test_when_no_user_handler(request: Request, user: AuthorizedUser):
        return json(user.model_dump())

    test_client = SanicASGITestClient(app)

    success_login_response = await get_success_login_response(test_client, without_user=True)

    request, response = await test_client.post(
        "/test_when_no_user",
        json=_login_params,
        headers={'Authorization': 'Bearer ' + success_login_response.token}
    )
    assert response.status == 401
