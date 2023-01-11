import inspect
from functools import wraps
from typing import Callable, Type, TypeVar, Generic, Dict, Optional, Union

from sanic.views import HTTPMethodView
from sanic.response import json as sanic_json

from pydantic import BaseModel, ValidationError
from pydantic.generics import GenericModel

from sanic_ext.exceptions import InitError
from sanic_ext.extensions.openapi.builders import OperationStore
from sanic_ext.utils.extraction import extract_request

from .Exceptions import _321CQUException

__all__ = ['ApiInterface', 'api_request', 'ApiResponse', 'api_response']

T = TypeVar("T")


class BaseApiResponse(GenericModel, Generic[T]):
    status: int
    msg: str
    data: T | None


class ApiResponse(BaseModel):
    pass


def api_request(
    json: Type[BaseModel] | None = None,
    form: Type[BaseModel] | None = None,
    query: Type[BaseModel] | None = None,
    body_argument: str = "body",
    query_argument: str = "query",
    **kwargs
) -> Callable[[T], T]:

    schemas: Dict[str, BaseModel] = {
        key: param
        for key, param in (
            ("json", json),
            ("form", form),
            ("query", query),
        )
    }

    if json and form:
        raise InitError("Cannot define both a form and json route validator")

    def decorator(f):
        body_content = {"application/json": json} if json is not None else \
            ({"application/x-www-form-urlencoded": form} if form else None)
        params = {**kwargs}

        @wraps(f)
        async def decorated_function(*args, **kwargs):
            request = extract_request(*args)
            try:
                if json:
                    kwargs[body_argument] = json.parse_obj(request.json)
                elif form:
                    kwargs[body_argument] = form.parse_obj(request.form)
                if query:
                    kwargs[query_argument] = query.parse_obj(request.args)
            except ValidationError as e:
                raise _321CQUException(message=f"请求参数错误，报错信息：{e.json()}")
            retval = f(*args, **kwargs)
            if inspect.isawaitable(retval):
                retval = await retval
            return retval

        if body_content is not None:
            if f in OperationStore():
                OperationStore()[decorated_function] = OperationStore().pop(f)
            OperationStore()[decorated_function].body(body_content, **params)
        return decorated_function

    return decorator


def api_response(retval: Optional[Union[Type[ApiResponse], Dict]] = None, status: int = 200, description: str = '',
                 **kwargs):
    def decorator(f):
        @wraps(f)
        async def decorated_function(*args, **kwargs):
            ret = f(*args, **kwargs)
            if inspect.isawaitable(ret):
                ret = await ret

            kwargs["status"] = status
            return sanic_json(BaseApiResponse(status=1, msg='success', data=ret).dict())

        if f in OperationStore():
            OperationStore()[decorated_function] = OperationStore().pop(f)

        if inspect.isclass(retval) and issubclass(retval, ApiResponse):
            OperationStore()[decorated_function].response(status, {'application/json': BaseApiResponse[retval]},
                                                          description, **kwargs)
        else:
            base_retval = {'status': 1, 'msg': 'success', 'data': retval if retval is not None else {}}
            OperationStore()[decorated_function].response(status, base_retval, description, **kwargs)
        return decorated_function

    return decorator


class ApiInterface(HTTPMethodView):
    pass
