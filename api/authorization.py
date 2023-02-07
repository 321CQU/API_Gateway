import inspect
from datetime import datetime, timedelta
from enum import StrEnum
from functools import wraps
from typing import Optional, Type, Any

from pydantic import BaseModel, ValidationError, Field
from sanic import Request, Blueprint
from jose import jwt
from sanic_ext.exceptions import InitError

from api.utils.ApiInterface import api_request, api_response

from utils.Exceptions import _321CQUException
from utils.Settings import ConfigManager

__all__ = ['authorization_blueprint', 'authorized', 'LoginApplyType', 'TokenPayload', 'AuthorizedUser']

authorization_blueprint = Blueprint('authorization', url_prefix='authorization')


class LoginApplyType(StrEnum):
    """
    Api请求类型
    """
    WX_Mini_APP = 'WX_Mini_APP'
    IOS_APP = 'IOS_APP'
    Announcement_Website = 'Announcement_Website'

    def check_api_key(self, api_key: str) -> bool:
        return api_key == ConfigManager().get_config('ApiKey', self.value())


class TokenPayload(BaseModel):
    timestamp: int
    applyType: LoginApplyType
    username: Optional[str]
    password: Optional[str]

    class Config:
        title = "token荷载"
        use_enum_values = True

    @classmethod
    def parse_obj(cls: Type['Model'], obj: Any) -> 'Model':
        try:
            return super().parse_obj(obj)
        except ValidationError as e:
            raise _321CQUException(error_info='Unauthorized', status_code=401, extra={'error': e.json()})


class _LoginRequest(BaseModel):
    apiKey: str = Field(title="api 请求密钥")
    applyType: LoginApplyType = Field(title='请求类型')
    username: Optional[str] = Field(title='用户账户')
    password: Optional[str] = Field(title='用户密码')

    class Config:
        title = "登陆请求值"


class _LoginResponse(BaseModel):
    token: str = Field(title='请求token', description='有效时间为15分钟')
    refreshToken: str = Field(title='刷新token', description='有效时间为7天')
    tokenExpireTime: int = Field(title='请求token过期时间戳')
    refreshTokenExpireTime: int = Field(title='刷新token过期时间戳')

    class Config:
        title = "登陆回传值"


@authorization_blueprint.post('login')
@api_request(json=_LoginRequest)
@api_response(_LoginResponse)
async def login(request: Request, body: _LoginRequest):
    """
    获取token

    小程序与APP调用时应将将统一身份认证账号密码作为参数上传以支持需要统一身份认证的相关API调用
    """
    if body.apiKey != ConfigManager().get_config('ApiKey', body.applyType):
        raise _321CQUException(error_info='Unauthorized', status_code=401)

    now = datetime.now()
    token_expire_time = int((now + timedelta(minutes=15)).timestamp())
    refresh_token_expire_time = int((now + timedelta(weeks=1)).timestamp())
    secret = ConfigManager().get_config('ApiKey', 'jwt_secret')
    token = jwt.encode(TokenPayload(timestamp=token_expire_time, applyType=body.applyType,
                                    username=body.username, password=body.password).dict(), secret)
    refresh_token = jwt.encode(TokenPayload(timestamp=refresh_token_expire_time,
                                            applyType=body.applyType,
                                            username=body.username, password=body.password).dict(), secret)

    return _LoginResponse(token=token, refreshToken=refresh_token,
                          tokenExpireTime=token_expire_time,
                          refreshTokenExpireTime=refresh_token_expire_time)


class _RefreshTokenRequest(BaseModel):
    refreshToken: str = Field(title='刷新token')

    class Config:
        title = "刷新token请求值"


class _RefreshTokenResponse(BaseModel):
    token: str = Field(title='请求token')
    tokenExpireTime: int = Field(title='请求token过期时间戳')

    class Config:
        title = "刷新token回传值"


def _decode_token(token: str) -> dict:
    if token is None:
        raise _321CQUException(error_info='Unauthorized', status_code=401)

    try:
        res = jwt.decode(token, ConfigManager().get_config('ApiKey', 'jwt_secret'))
    except jwt.JWTError as e:
        raise _321CQUException(error_info='Unauthorized', status_code=401, extra={'error': e})

    return res


@authorization_blueprint.post('refreshToken')
@api_request(json=_RefreshTokenRequest)
@api_response(_RefreshTokenResponse)
async def refresh_token(request: Request, body: _RefreshTokenRequest):
    """
    刷新token
    """
    if body.refreshToken is None:
        raise _321CQUException(error_info='Unauthorized', status_code=401)

    payload = TokenPayload.parse_obj(
        _decode_token(body.refreshToken)
    )

    if payload.timestamp < datetime.now().timestamp():
        raise _321CQUException(error_info='Token Expired', status_code=401)

    token_expire_time = int((datetime.now() + timedelta(minutes=15)).timestamp())
    token = jwt.encode(TokenPayload(timestamp=token_expire_time, applyType=payload.applyType,
                                    username=payload.username, password=payload.password).dict(),
                       ConfigManager().get_config('ApiKey', 'jwt_secret'))
    return _RefreshTokenResponse(token=token, tokenExpireTime=token_expire_time)


class AuthorizedUser(BaseModel):
    username: str
    password: str

    class Config:
        title = "经验证的用户"


def authorized(*, include: Optional[list[LoginApplyType]] = None, exclude: Optional[list[LoginApplyType]] = None,
               need_user: bool = False, user_argument: str = 'user'):
    """
    api权限校验装饰器
    :param include: 可以使用该api的权限请求方式
    :param exclude: 无法使用该api权限的请求方式
    :param need_user: 需要从token中获取用户
    :param user_argument: 注入到参数中的变量名称
    """
    if include and exclude:
        raise InitError("Cannot set include and exclude at same time")

    def decorator(f):
        @wraps(f)
        async def wrapped_function(request: Request, *args, **kwargs):
            payload = TokenPayload.parse_obj(_decode_token(request.token))
            if payload.timestamp < datetime.now().timestamp():
                raise _321CQUException(error_info='Token Expired', status_code=401)

            if (payload.applyType in exclude if exclude is not None else False) \
                    or (payload.applyType not in include if include is not None else False):
                raise _321CQUException(error_info='No Access', status_code=403)

            if need_user:
                if payload.username is None or payload.password is None:
                    raise _321CQUException(error_info='User Info Not Found', status_code=401)
                kwargs[user_argument] = AuthorizedUser(username=payload.username, password=payload.password)

            retval = f(request, *args, **kwargs)
            if inspect.isawaitable(retval):
                retval = await retval
            return retval

        return wrapped_function

    return decorator
