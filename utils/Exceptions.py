import json as json_lib
from typing import Optional, Union, Dict, Any

from sanic.exceptions import SanicException
from sanic.handlers import ErrorHandler
from sanic.log import error_logger
from sanic.response import json


_SENSITIVE_KEYS = {
    "token",
    "authorization",
    "apikey",
    "api_key",
    "refresh_token",
    "refreshtoken",
    "password",
}
_REDACTED_VALUE = "<redacted>"


def _redact_sensitive_data(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: (_REDACTED_VALUE if str(key).lower() in _SENSITIVE_KEYS else _redact_sensitive_data(item))
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact_sensitive_data(item) for item in value]
    return value


def _redact_request_body(body: bytes) -> str:
    if not body:
        return ""

    body_text = body.decode(errors="replace")
    try:
        return json_lib.dumps(_redact_sensitive_data(json_lib.loads(body_text)), ensure_ascii=False)
    except json_lib.JSONDecodeError:
        return _REDACTED_VALUE


class _321CQUException(SanicException):
    status_code = 200
    quite = True

    def __init__(
            self,
            error_info: Optional[str] = None,
            message: Optional[Union[str, bytes]] = None,
            status_code: Optional[int] = None,
            quite: Optional[bool] = None,
            context: Optional[Dict[str, Any]] = None,
            extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message, status_code, quiet=quite, context=context, extra=extra)
        self.error_info = error_info if error_info is not None else ""
        if quite is not None:
            self.quite = quite


class _321CQUErrorHandler(ErrorHandler):
    def default(self, request, exception: SanicException):
        if isinstance(exception, _321CQUException):
            self.log(request, exception)
            if not exception.quite:
                error_logger.exception(
                    f"request token is {_REDACTED_VALUE}, request param is {_redact_request_body(request.body)}"
                )
            return json({'status': 0, 'msg': exception.error_info, 'data': exception.context},
                        status=exception.status_code)
        else:
            return super().default(request, exception)
