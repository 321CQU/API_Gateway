from typing import Optional, Union, Dict, Any

from pydantic import ValidationError

from sanic.exceptions import SanicException
from sanic.handlers import ErrorHandler
from sanic.response import json
from sanic.log import error_logger


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
        super().__init__(message, status_code, quite, context, extra)
        self.error_info = error_info if error_info is not None else ""


class _321CQUErrorHandler(ErrorHandler):
    def default(self, request, exception: SanicException):
        if isinstance(exception, _321CQUException):
            self.log(request, exception)
            if not exception.quite:
                error_logger.exception(f"request token is {request.token}, request param is {request.body.decode()}")
            return json({'status': 0, 'msg': exception.error_info, 'data': exception.context},
                        status=exception.status_code)
        else:
            return super().default(request, exception)


