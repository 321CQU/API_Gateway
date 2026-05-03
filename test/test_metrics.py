import pytest
from sanic import Sanic
from sanic.response import json
from sanic_testing.testing import SanicASGITestClient

from utils.Metrics import register_metrics


_METRICS_HEADERS = {"Authorization": "Bearer test-metrics-token"}


def _register_metrics_with_token(app: Sanic) -> None:
    app.config.METRICS_TOKEN = "test-metrics-token"
    register_metrics(app)


@pytest.mark.asyncio
async def test_metrics_endpoint_exposes_prometheus_text():
    app = Sanic("MetricsTest")
    _register_metrics_with_token(app)

    _, response = await SanicASGITestClient(app).get("/metrics", headers=_METRICS_HEADERS)

    assert response.status == 200
    assert response.content_type.startswith("text/plain")
    assert "api_gateway_http_request_duration_seconds" in response.text


@pytest.mark.asyncio
async def test_metrics_endpoint_rejects_invalid_token():
    app = Sanic("MetricsAuthTest")
    _register_metrics_with_token(app)

    _, response = await SanicASGITestClient(app).get("/metrics")

    assert response.status == 403


@pytest.mark.asyncio
async def test_metrics_records_http_request_duration_by_route_and_status():
    app = Sanic("MetricsRouteTest")

    @app.get("/hello/<name>")
    async def hello(request, name):
        return json({"name": name})

    _register_metrics_with_token(app)
    client = SanicASGITestClient(app)

    _, response = await client.get("/hello/world")
    assert response.status == 200

    _, metrics_response = await client.get("/metrics", headers=_METRICS_HEADERS)

    assert 'api_gateway_http_requests_total{method="GET",route="/hello/<name:str>",status_code="200"}' in metrics_response.text
    assert 'api_gateway_http_request_duration_seconds_count{method="GET",route="/hello/<name:str>",status_code="200"}' in metrics_response.text


@pytest.mark.asyncio
async def test_metrics_records_error_responses():
    app = Sanic("MetricsErrorTest")

    @app.get("/unavailable")
    async def unavailable(request):
        return json({"error": "unavailable"}, status=503)

    _register_metrics_with_token(app)
    client = SanicASGITestClient(app)

    _, response = await client.get("/unavailable")
    assert response.status == 503

    _, metrics_response = await client.get("/metrics", headers=_METRICS_HEADERS)

    assert 'api_gateway_http_errors_total{method="GET",route="/unavailable",status_code="503"}' in metrics_response.text


@pytest.mark.asyncio
async def test_metrics_uses_fixed_label_for_unmatched_routes():
    app = Sanic("MetricsUnmatchedRouteTest")
    _register_metrics_with_token(app)
    client = SanicASGITestClient(app)

    _, response = await client.get("/missing/path/123")
    assert response.status == 404

    _, metrics_response = await client.get("/metrics", headers=_METRICS_HEADERS)

    assert 'api_gateway_http_requests_total{method="GET",route="__unmatched__",status_code="404"}' in metrics_response.text
    assert "/missing/path/123" not in metrics_response.text
