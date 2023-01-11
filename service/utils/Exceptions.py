from sanic.exceptions import SanicException
from sanic.handlers import ErrorHandler
from sanic.response import json


class _321CQUException(SanicException):
    status_code = 200


class _321CQUErrorHandler(ErrorHandler):
    def default(self, request, exception: SanicException):
        if isinstance(exception, _321CQUException):
            return json({'status': 0, 'msg': exception.message, 'data': exception.context},
                        status=exception.status_code)
        else:
            return super().default(request, exception)


