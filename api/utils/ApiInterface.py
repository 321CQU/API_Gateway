import inspect
from functools import wraps
from typing import Callable, Type, TypeVar, Generic, Dict, Optional, Union

from sanic.response import HTTPResponse

from sanic_ext.exceptions import InitError
from sanic_ext.extensions.openapi.builders import OperationStore
from sanic_ext.utils.extraction import extract_request

from pydantic import BaseModel, ValidationError, Field, SerializeAsAny

from grpc.aio import AioRpcError
from grpc import StatusCode

from api.utils.tools import component
from utils.Exceptions import _321CQUException

__all__ = ['api_request', 'api_response', 'handle_grpc_error']

T = TypeVar("T", bound=BaseModel)


class BaseApiResponse(BaseModel, Generic[T]):
    """
    API响应模版，回传的ApiResponse子类会填入data中
    """
    status: int = Field(title='响应状态', description='成功时为1，失败时为0')
    msg: str = Field(title='响应信息', description='成功时为`success`，失败时为相关错误提示')
    data: SerializeAsAny[T | dict] = Field(title="数据")


def api_request(
        json: Type[BaseModel] | None = None,
        form: Type[BaseModel] | None = None,
        query: Type[BaseModel] | None = None,
        body_argument: str = "body",
        query_argument: str = "query",
        **kwargs
) -> Callable:
    """
    实现请求参数校验即OpenAPI文档生成的装饰器

    **json和form不能同时被设置**

    :param json: 请求体以json格式读取后应当对应的数据模型
    :param form: 请求体以form格式读取后应当对应的数据模型
    :param query: 路由查询参数读取后应对应的数据模型
    :param body_argument: 请求体中参数应当注入的名字，默认为"body"
    :param query_argument: 路由查询参数应当注入的名字，默认为"body"
    :param kwargs: 其他需要显示在/docs中的参数（需满足OpenAPI规范）
    """

    if json and form:
        raise InitError("Cannot define both a form and json route validator")

    def decorator(f):
        title = json.model_config.get("title") if json is not None else \
            (form.model_config.get("title") if form is not None else None)
        body_content = {
            "application/json": component(json)
        } if json is not None else (
            {
                "application/x-www-form-urlencoded": component(form)
            } if form is not None else None
        )
        params = {**kwargs}

        @wraps(f)
        async def decorated_function(*args, **kwargs):
            request = extract_request(*args)
            try:
                if json:
                    kwargs[body_argument] = json.model_validate(request.json)
                elif form:
                    kwargs[body_argument] = form.model_validate(request.form)
                if query:
                    parsed_args = {}
                    for key, value in request.args.items():
                        parsed_args[key] = value[0] if len(value) == 1 else value
                    kwargs[query_argument] = query.model_validate(parsed_args)
            except ValidationError as e:
                raise _321CQUException(error_info=f"请求参数错误", quite=True)
            retval = f(*args, **kwargs)
            if inspect.isawaitable(retval):
                retval = await retval
            return retval

        # 使用sanic-ext中的OperationStore实现文档自动生成，参考其中的openapi.body装饰器
        if f in OperationStore():
            OperationStore()[decorated_function] = OperationStore().pop(f)
        if body_content is not None:
            OperationStore()[decorated_function].body(body_content, **params)
        if query is not None:
            schema = query.model_json_schema(ref_template="#/components/schemas/{model}")
            for name, value in inspect.get_annotations(query).items():
                ex_param = {}
                if schema.get('properties') is not None and schema['properties'].get(name) is not None:
                    ex_param = schema['properties'][name]

                description = (ex_param.get('title') if ex_param.get('title') else '') + (
                    ex_param.get('description') if ex_param.get('description') else '')
                if description == '':
                    description = None

                OperationStore()[decorated_function].parameter(name, value, 'query', description=description)
        return decorated_function

    return decorator


def api_response(retval: Optional[Union[Type[BaseModel], Dict, HTTPResponse]] = None, status: int = 200,
                 description: str = '',
                 *, auto_wrap: bool = True, **kwargs):
    """
    实现参数返回值自动包装与API页面生成的装饰器
    :param retval: 返回值信息，可以为ApiResponse的子类或字典，为空则返回值中data项置None
    :param status: Response Http相应码
    :param description: 返回值相关描述，显示在/docs页面中
    :param auto_wrap: 强制关键字参数，为False时直接返回被装饰函数运行结果
    :param kwargs: 其他需要显示在/docs中的参数（需满足OpenAPI规范）
    """

    def decorator(f):
        @wraps(f)
        async def decorated_function(*args, **kwargs):
            ret = f(*args, **kwargs)
            if inspect.isawaitable(ret):
                ret = await ret

            kwargs["status"] = status
            if auto_wrap:
                return HTTPResponse(
                    BaseApiResponse[(retval if retval is not None else Dict)](
                        status=1, msg='success', data=(ret if ret is not None else {})
                    ).model_dump_json(),
                    content_type="application/json")
            else:
                return ret

        # 使用sanic-ext中的OperationStore实现文档自动生成，参考其中的openapi.body装饰器
        if f in OperationStore():
            OperationStore()[decorated_function] = OperationStore().pop(f)

        if auto_wrap:
            if inspect.isclass(retval) and issubclass(retval, BaseModel):
                OperationStore()[decorated_function].response(
                    status, {
                        'application/json': component(BaseApiResponse[retval])
                    },
                    description, **kwargs
                )
            else:
                base_retval = {'status': 1, 'msg': 'success', 'data': retval}
                OperationStore()[decorated_function].response(
                    status, {'application/json': component(BaseApiResponse[Dict])}, description, **kwargs)
        else:
            OperationStore()[decorated_function].response(status, retval, description, **kwargs)
        return decorated_function

    return decorator


def handle_grpc_error(func):
    """
    处理AioRpcError，返回的HttpResponse中包含503与grpc报错详细信息
    """

    @wraps(func)
    async def wrapped_function(*args, **kwargs):
        try:
            ret = func(*args, **kwargs)
            if inspect.isawaitable(ret):
                ret = await ret
            return ret
        except AioRpcError as e:
            if e.code() == StatusCode.UNAVAILABLE:
                raise _321CQUException(error_info=e.details() if e.details() is not None else "服务调用异常",
                                       extra=e.details(), status_code=503, quite=False)
            elif e.code() == StatusCode.INVALID_ARGUMENT:
                raise _321CQUException(error_info=e.details() if e.details() is not None else "服务调用异常",
                                       extra=e.details(), status_code=503, quite=True)
            raise _321CQUException(error_info="服务调用异常", extra=e.details(), status_code=503, quite=False)

    return wrapped_function
