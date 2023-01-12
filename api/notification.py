from pydantic import BaseModel

from sanic import Request, Blueprint

from service.notification_center.proto.apns_pb2 import SetUserApnsRequest, DefaultResponse
from service.notification_center.proto.apns_pb2_grpc import ApnsStub
from service.gRPCManager import gRPCManager, ServiceEnum

from api.utils.ApiInterface import api_request, api_response, ApiResponse, handle_grpc_error

from utils.Exceptions import _321CQUException


__all__ = ['notification_blueprint']

notification_blueprint = Blueprint('notification', url_prefix='/notification')


class _SetUserApnsRequest(BaseModel):
    sid: str
    apn: str


@notification_blueprint.post(uri='set_apns')
@api_request(json=_SetUserApnsRequest)
@api_response()
@handle_grpc_error
async def set_user_apns(request: Request, body: _SetUserApnsRequest):
    async with gRPCManager().get_stub(ServiceEnum.NotificationCenter) as stub:
        stub: ApnsStub = stub
        res: DefaultResponse = await stub.SetUserApns(SetUserApnsRequest(sid=body.sid, apn=body.apn))
        if res.status == 1:
            return
        else:
            raise _321CQUException(error_info=res.msg, extra=res.data)
