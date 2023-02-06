from typing import List, Dict

import google.protobuf.message
from pydantic import BaseModel, Field
from sanic import Request, Blueprint
from google.protobuf.json_format import MessageToDict

from _321CQU.tools import gRPCManager, ServiceEnum
import micro_services_protobuf.edu_admin_center.eac_service_pb2_grpc as eac_grpc
import micro_services_protobuf.edu_admin_center.eac_models_pb2 as eac_models
import micro_services_protobuf.mycqu_service.mycqu_request_response_pb2 as mycqu_rr
import micro_services_protobuf.mycqu_service.mycqu_model_pb2 as mycqu_model
from micro_services_protobuf.model.exam import Exam
from micro_services_protobuf.model.score import Score

from api.authorization import authorized, LoginApplyType, AuthorizedUser
from api.utils.ApiInterface import api_request, api_response, handle_grpc_error, ApiResponse

from utils.Exceptions import _321CQUException


__all__ = ['edu_admin_center_blueprint']

edu_admin_center_blueprint = Blueprint('EduAdminCenter', url_prefix='/notification')


def _message_to_dict(message: google.protobuf.message.Message) -> Dict:
    return MessageToDict(message, including_default_value_fields=True, preserving_proto_field_name=True)


class _ValidateAuthResponse(ApiResponse):
    sid: str = Field(title="学号")
    auth: str = Field(title="统一身份认证号")
    name: str = Field(title="姓名")

    class Config:
        title = "验证账号回传值"


@edu_admin_center_blueprint.post(uri='validateAuth')
@api_request()
@api_response(_ValidateAuthResponse)
@authorized(need_user=True)
@handle_grpc_error
async def validate_auth(request: Request, user: AuthorizedUser, grpc_manager: gRPCManager):
    """
    账号验证
    """
    async with grpc_manager.get_stub(ServiceEnum.EduAdminCenter) as stub:
        stub: eac_grpc.EduAdminCenterStub = stub
        res: eac_models.ValidateAuthResponse = await stub.ValidateAuth(
            mycqu_rr.BaseLoginInfo(auth=user.username, password=user.password)
        )
        return _ValidateAuthResponse(sid=res.sid, auth=res.auth, name=res.name)


class _FetchExamRequest(BaseModel):
    sid: str = Field(title="学号")

    class Config:
        title = "考表获取请求值"


class _FetchExamResponse(ApiResponse):
    exams: List[Exam] = Field(title="考试列表")

    class Config:
        title = "考表获取回传值"


@edu_admin_center_blueprint.post(uri='fetchExam')
@api_request(json=_FetchExamRequest)
@api_response(_FetchExamResponse)
@authorized(need_user=True)
@handle_grpc_error
async def fetch_exam(request: Request, body: _FetchExamRequest, user: AuthorizedUser, grpc_manager: gRPCManager):
    """
    考试安排
    """
    async with grpc_manager.get_stub(ServiceEnum.EduAdminCenter) as stub:
        stub: eac_grpc.EduAdminCenterStub = stub
        res: mycqu_rr.FetchExamResponse = await stub.FetchExam(
            mycqu_rr.FetchExamRequest(base_login_info=mycqu_rr.BaseLoginInfo(auth=user.username, password=user.password),
                                      stu_id=body.sid)
        )
        return _FetchExamResponse.parse_obj(_message_to_dict(res))


class _FetchScoreRequest(BaseModel):
    sid: str = Field(title="学号")
    is_minor: bool = Field(title="是否获取辅修成绩")

    class Config:
        title = "成绩查询请求值"


class _FetchScoreResponse(ApiResponse):
    scores: List[Score] = Field(title="成绩")

    class Config:
        title = "成绩查询回传值"


@edu_admin_center_blueprint.post(uri='fetchScore')
@api_request(json=_FetchScoreRequest)
@api_response(_FetchScoreResponse)
@authorized(need_user=True)
@handle_grpc_error
async def fetch_score(request: Request, body: _FetchScoreRequest, user: AuthorizedUser, grpc_manager: gRPCManager):
    """
    成绩查询
    """
    async with grpc_manager.get_stub(ServiceEnum.EduAdminCenter) as stub:
        stub: eac_grpc.EduAdminCenterStub = stub
        res: mycqu_rr.FetchScoreResponse = await stub.FetchScore(
            eac_models.FetchScoreRequest(base_login_info=mycqu_rr.BaseLoginInfo(auth=user.username, password=user.password),
                                         sid=body.sid,
                                         is_minor=body.is_minor))
        return _FetchScoreResponse.parse_obj(_message_to_dict(res))
