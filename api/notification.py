import json
from typing import List, Optional, Dict

from pydantic import BaseModel, Field, Json

from sanic import Request, Blueprint

from _321CQU.tools import gRPCManager
from _321CQU.service import ServiceEnum
from micro_services_protobuf.notification_center import service_pb2_grpc as notification_grpc
from micro_services_protobuf.notification_center import wechat_pb2, apns_pb2, event_pb2
from micro_services_protobuf.common_pb2 import DefaultResponse, UserId
from micro_services_protobuf.protobuf_enum.notification_center import NotificationEvent

from api.authorization import authorized, LoginApplyType, AuthorizedUser
from api.utils.ApiInterface import api_request, api_response, handle_grpc_error

from utils.Exceptions import _321CQUException

__all__ = ['notification_blueprint']

notification_blueprint = Blueprint('notification', url_prefix='/notification')


class _UpdateSubscribeRequest(BaseModel):
    """
    更新订阅信息请求值
    """
    uid: str = Field(title='用户身份标识符')
    event: NotificationEvent = Field(title="欲操作事件类型", description=NotificationEvent.get_all_events_description())
    is_subscribe: bool = Field(title="是否为订阅操作，true为订阅，false为取消订阅")
    extra_data: Optional[Dict] = Field(title='订阅事件可能需要的额外信息，任意字典')


@notification_blueprint.post(uri='updateSubscribe')
@api_request(json=_UpdateSubscribeRequest)
@api_response()
@authorized(need_user=True)
@handle_grpc_error
async def update_subscribe(request: Request, body: _UpdateSubscribeRequest, user: AuthorizedUser,
                           grpc_manager: gRPCManager):
    """
    更新通知订阅设置
    """
    async with grpc_manager.get_stub(ServiceEnum.NotificationService) as stub:
        stub: notification_grpc.NotificationStub = stub
        res: DefaultResponse = await stub.UpdateEventSubscribe(
            event_pb2.UpdateEventSubscribeRequest(
                uid=bytes.fromhex(body.uid), event=body.event.value, is_subscribe=body.is_subscribe,
                extra_data=event_pb2.UpdateEventSubscribeRequest.ExtraData(
                    auth=user.username, password=user.password,
                    extra_data=(json.dumps(body.extra_data) if body.extra_data is not None else None)))
        )
        if res.msg == 'success':
            return
        else:
            raise _321CQUException(error_info=res.msg)


class _FetchSubscribeInfoRequest(BaseModel):
    """
    获取订阅信息请求值
    """
    uid: str = Field(title='用户身份标识符')


class _FetchSubscribeInfoResponse(BaseModel):
    """
    获取订阅信息响应值
    """
    events: List[NotificationEvent] = Field(title="已订阅的事件列表",
                                            description=NotificationEvent.get_all_events_description())


@notification_blueprint.post(uri='fetchSubscribeInfo')
@api_request(json=_FetchSubscribeInfoRequest)
@api_response(_FetchSubscribeInfoResponse)
@authorized()
@handle_grpc_error
async def fetch_subscribe_info(request: Request, body: _FetchSubscribeInfoRequest, grpc_manager: gRPCManager):
    """
    获取订阅信息
    """
    async with grpc_manager.get_stub(ServiceEnum.NotificationService) as stub:
        stub: notification_grpc.NotificationStub = stub
        res: event_pb2.FetchSubscribeInfoResponse = await stub.FetchSubscribeInfo(UserId(uid=bytes.fromhex(body.uid)))
        events = list(map(lambda x: NotificationEvent(x), res.events))
        return _FetchSubscribeInfoResponse(events=events)


class _SetUserApnsRequest(BaseModel):
    """设置用户Apns请求值"""
    uid: str = Field(title='用户身份标识')
    apn: str = Field(title='设备apn代码')


@notification_blueprint.post(uri='setApns')
@api_request(json=_SetUserApnsRequest)
@api_response()
@authorized(include=[LoginApplyType.IOS_APP])
@handle_grpc_error
async def set_user_apns(request: Request, body: _SetUserApnsRequest, grpc_manager: gRPCManager):
    """
    设置APNs(Apple Push Notification Service)调用

    **仅支持IOS客户端调用**
    """
    async with grpc_manager.get_stub(ServiceEnum.ApnsService) as stub:
        stub: notification_grpc.ApnsStub = stub
        res: DefaultResponse = await stub.SetUserApns(
            apns_pb2.SetUserApnsRequest(uid=bytes.fromhex(body.uid), apn=bytes.fromhex(body.apn)))
        if res.msg == 'success':
            return
        else:
            raise _321CQUException(error_info=res.msg)
    return


class BindOpenIdRequest(BaseModel):
    uid: str = Field(title='用户身份标识符')
    code: str = Field(title='openid获取码')


@notification_blueprint.post(uri='bindOpenId')
@api_request(json=BindOpenIdRequest)
@api_response()
@authorized(include=[LoginApplyType.WX_Mini_APP])
@handle_grpc_error
async def bind_openid(request: Request, body: BindOpenIdRequest, grpc_manager: gRPCManager):
    """
    绑定用户openid

    **仅支持微信小程序调用**
    """
    async with grpc_manager.get_stub(ServiceEnum.WechatService) as stub:
        stub: notification_grpc.WechatStub = stub
        res: DefaultResponse = await stub.SetUserOpenId(wechat_pb2.SetUserOpenIdRequest(uid=bytes.fromhex(body.uid),
                                                                                        code=body.code))
        if res.msg == 'success':
            return
        else:
            raise _321CQUException(error_info=res.msg)
