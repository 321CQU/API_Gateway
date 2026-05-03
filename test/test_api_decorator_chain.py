from uuid import uuid4
from types import SimpleNamespace

import pytest
from grpc import StatusCode
from grpc.aio import AioRpcError
from pydantic import BaseModel
from sanic import Sanic, Request
from sanic_testing.testing import SanicASGITestClient

from api.authorization import authorized
from api.utils.ApiInterface import api_request, api_response, handle_grpc_error
from utils.Exceptions import _321CQUException, _321CQUErrorHandler


def _test_app() -> Sanic:
    app = Sanic(f"decorator_chain_{uuid4().hex}")
    app.error_handler = _321CQUErrorHandler()
    return app


def _call_error_handler(body: bytes, monkeypatch):
    logged_messages = []
    handler = _321CQUErrorHandler()
    request = SimpleNamespace(
        app=SimpleNamespace(config=SimpleNamespace(FALLBACK_ERROR_FORMAT="auto")),
        body=body,
        token="plain-token",
    )

    monkeypatch.setattr(
        "utils.Exceptions.error_logger.exception",
        lambda message: logged_messages.append(message),
    )
    monkeypatch.setattr(handler, "log", lambda request, exception: None)

    response = handler.default(
        request,
        _321CQUException(error_info="failed", status_code=500, quite=False),
    )

    return response, logged_messages[0]


class _Body(BaseModel):
    name: str


class _Query(BaseModel):
    page: int


class _Result(BaseModel):
    value: str


@pytest.mark.asyncio
async def test_api_request_validation_failure_returns_standard_error():
    app = _test_app()

    @app.post("/validation")
    @api_request(json=_Body)
    @api_response(_Result)
    async def validation_handler(request: Request, body: _Body):
        return _Result(value=body.name)

    _, response = await SanicASGITestClient(app).post("/validation", json={})

    assert response.status == 200
    assert response.json == {"status": 0, "msg": "请求参数错误", "data": None}


@pytest.mark.asyncio
async def test_api_request_and_response_wrap_success_payload():
    app = _test_app()

    @app.get("/wrapped")
    @api_request(query=_Query)
    @api_response(_Result)
    async def wrapped_handler(request: Request, query: _Query):
        return _Result(value=str(query.page))

    _, response = await SanicASGITestClient(app).get("/wrapped?page=3")

    assert response.status == 200
    assert response.json == {"status": 1, "msg": "success", "data": {"value": "3"}}


@pytest.mark.asyncio
async def test_authorized_rejects_missing_token_before_handler_runs():
    app = _test_app()

    @app.get("/auth")
    @api_response(_Result)
    @authorized()
    async def auth_handler(request: Request):
        return _Result(value="called")

    _, response = await SanicASGITestClient(app).get("/auth")

    assert response.status == 401
    assert response.json == {"status": 0, "msg": "Unauthorized", "data": None}


@pytest.mark.asyncio
async def test_handle_grpc_error_converts_rpc_error_to_503():
    app = _test_app()

    @app.get("/grpc")
    @api_response(_Result)
    @handle_grpc_error
    async def grpc_handler(request: Request):
        raise AioRpcError(StatusCode.UNAVAILABLE, (), (), "backend unavailable")

    _, response = await SanicASGITestClient(app).get("/grpc")

    assert response.status == 503
    assert response.json == {"status": 0, "msg": "backend unavailable", "data": None}


@pytest.mark.asyncio
async def test_error_handler_redacts_token_and_sensitive_body_fields(monkeypatch):
    response, logged_message = _call_error_handler(
        (
            b'{"apiKey":"plain-api-key","password":"plain-password",'
            b'"nested":{"refreshToken":"plain-refresh-token","visible":"kept"}}'
        ),
        monkeypatch,
    )

    assert response.status == 500
    assert "plain-token" not in logged_message
    assert "plain-api-key" not in logged_message
    assert "plain-password" not in logged_message
    assert "plain-refresh-token" not in logged_message
    assert '"visible": "kept"' in logged_message


@pytest.mark.asyncio
async def test_error_handler_redacts_non_json_body(monkeypatch):
    response, logged_message = _call_error_handler(
        b"password=plain-password&token=plain-token&visible=kept",
        monkeypatch,
    )

    assert response.status == 500
    assert "plain-password" not in logged_message
    assert "plain-token" not in logged_message
    assert "visible=kept" not in logged_message
