import hmac
import time
from ipaddress import ip_address

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from sanic import Request, Sanic
from sanic.response import HTTPResponse, raw, text

from utils.Settings import ConfigManager

HTTP_REQUEST_DURATION = Histogram(
    "api_gateway_http_request_duration_seconds",
    "API Gateway HTTP request duration in seconds.",
    ("method", "route", "status_code"),
)

HTTP_REQUESTS_TOTAL = Counter(
    "api_gateway_http_requests_total",
    "Total API Gateway HTTP requests.",
    ("method", "route", "status_code"),
)

HTTP_ERRORS_TOTAL = Counter(
    "api_gateway_http_errors_total",
    "Total API Gateway HTTP error responses.",
    ("method", "route", "status_code"),
)


def _get_route_label(request: Request) -> str:
    route = getattr(request, "route", None)
    route_path = getattr(route, "path", None)
    if route_path:
        return route_path if route_path.startswith("/") else f"/{route_path}"
    return "__unmatched__"


def _get_metrics_token() -> str | None:
    return ConfigManager().get_config("Metrics", "token") or None


def _is_loopback_request(request: Request) -> bool:
    client_ip = getattr(request, "remote_addr", None) or getattr(request, "ip", None)
    if client_ip is None:
        return False

    try:
        return ip_address(client_ip).is_loopback
    except (ValueError, TypeError):
        return False


def _is_metrics_request_allowed(request: Request) -> bool:
    token = _get_metrics_token()
    if token is None:
        return _is_loopback_request(request)

    authorization = request.headers.get("Authorization", "")
    scheme, _, credentials = authorization.partition(" ")
    return scheme.lower() == "bearer" and hmac.compare_digest(credentials, token)


def register_metrics(app: Sanic) -> None:
    @app.get("/metrics", name="metrics")
    async def metrics(request: Request) -> HTTPResponse:
        if not _is_metrics_request_allowed(request):
            return text("Forbidden", status=403)
        return raw(generate_latest(), content_type=CONTENT_TYPE_LATEST)

    @app.middleware("request")
    async def record_request_start(request: Request) -> None:
        if request.path == "/metrics":
            return
        request.ctx.metrics_start_time = time.perf_counter()

    @app.middleware("response")
    async def record_request_metrics(request: Request, response: HTTPResponse) -> None:
        start_time = getattr(request.ctx, "metrics_start_time", None)
        if start_time is None:
            return

        method = request.method
        route = _get_route_label(request)
        status_code = str(response.status)
        duration = time.perf_counter() - start_time

        HTTP_REQUEST_DURATION.labels(method, route, status_code).observe(duration)
        HTTP_REQUESTS_TOTAL.labels(method, route, status_code).inc()
        if response.status >= 400:
            HTTP_ERRORS_TOTAL.labels(method, route, status_code).inc()
