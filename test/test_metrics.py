import pytest
from sanic import Sanic
from sanic.response import json
from sanic_testing.testing import SanicASGITestClient

from utils.Metrics import register_metrics


@pytest.mark.asyncio
async def test_metrics_endpoint_exposes_prometheus_text():
    app = Sanic("MetricsTest")
    register_metrics(app)

    _, response = await SanicASGITestClient(app).get("/metrics")

    assert response.status == 200
    assert response.content_type.startswith("text/plain")
    assert "api_gateway_http_request_duration_seconds" in response.text


@pytest.mark.asyncio
async def test_metrics_records_http_request_duration_by_route_and_status():
    app = Sanic("MetricsRouteTest")

    @app.get("/hello/<name>")
    async def hello(request, name):
        return json({"name": name})

    register_metrics(app)
    client = SanicASGITestClient(app)

    _, response = await client.get("/hello/world")
    assert response.status == 200

    _, metrics_response = await client.get("/metrics")

    assert 'api_gateway_http_requests_total{method="GET",route="/hello/<name:str>",status_code="200"}' in metrics_response.text
    assert 'api_gateway_http_request_duration_seconds_count{method="GET",route="/hello/<name:str>",status_code="200"}' in metrics_response.text
