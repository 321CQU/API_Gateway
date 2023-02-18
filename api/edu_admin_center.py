from typing import List, Dict, Any, Generator, Callable

import google.protobuf.message
from pydantic import BaseModel, Field, errors
from sanic import Request, Blueprint
from google.protobuf.json_format import MessageToDict

from _321CQU.tools import gRPCManager
from _321CQU.service import ServiceEnum
import micro_services_protobuf.edu_admin_center.eac_service_pb2_grpc as eac_grpc
import micro_services_protobuf.edu_admin_center.eac_models_pb2 as eac_models
import micro_services_protobuf.mycqu_service.mycqu_request_response_pb2 as mycqu_rr
import micro_services_protobuf.mycqu_service.mycqu_model_pb2 as mycqu_model
from micro_services_protobuf.model.exam import Exam
from micro_services_protobuf.model.score import Score, GpaRanking
from micro_services_protobuf.model.enroll import EnrollCourseInfo, EnrollCourseItem
from micro_services_protobuf.model.course import CourseTimetable

from api.authorization import authorized, LoginApplyType, AuthorizedUser
from api.utils.ApiInterface import api_request, api_response, handle_grpc_error

from utils.Exceptions import _321CQUException


__all__ = ['edu_admin_center_blueprint']

edu_admin_center_blueprint = Blueprint('EduAdminCenter', url_prefix='/edu_admin_center')


def _message_to_dict(message: google.protobuf.message.Message) -> Dict:
    return MessageToDict(message, including_default_value_fields=True, preserving_proto_field_name=True)


class _ValidateAuthResponse(BaseModel):
    sid: str = Field(title="学号")
    auth: str = Field(title="统一身份认证号")
    name: str = Field(title="姓名")
    uid: str = Field(title="用户身份标识")

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
        return _ValidateAuthResponse(sid=res.sid, auth=res.auth, name=res.name, uid=res.uid.hex())


class _FetchEnrollCourseInfoRequest(BaseModel):
    is_major: bool = Field(title="是否获取主修课程")

    class Config:
        title = "获取可选课程信息请求值"


class _FetchEnrollCourseInfoResponse(BaseModel):
    result: Dict[str, List[EnrollCourseInfo]] = Field(title="搜索结果", description="按照课程类别、课程方式组织，如{'主修课程': [...]}")

    class Config:
        title = "获取可选课程信息回传值"


@edu_admin_center_blueprint.post(uri='fetchEnrollCourseInfo')
@api_request(json=_FetchEnrollCourseInfoRequest)
@api_response(_FetchEnrollCourseInfoResponse)
@authorized(include=[LoginApplyType.IOS_APP], need_user=True)
@handle_grpc_error
async def fetch_enroll_course_info(request: Request, body: _FetchEnrollCourseInfoRequest, user: AuthorizedUser, grpc_manager: gRPCManager):
    """
    可选课程查询

    **仅支持IOS客户端调用**
    """
    async with grpc_manager.get_stub(ServiceEnum.EduAdminCenter) as stub:
        stub: eac_grpc.EduAdminCenterStub = stub
        res: mycqu_rr.FetchEnrollCourseInfoResponse = await stub.FetchEnrollCourseInfo(
            mycqu_rr.FetchEnrollCourseInfoRequest(
                base_login_info=mycqu_rr.BaseLoginInfo(auth=user.username, password=user.password),
                is_major=body.is_major)
        )
        result = {}
        for k, v in res.result.items():
            result[k] = list(map(lambda x: EnrollCourseInfo.parse_obj(_message_to_dict(x)), v.info))
        return _FetchEnrollCourseInfoResponse(result=result)


class _FetchEnrollCourseItemRequest(BaseModel):
    id: str = Field(title="需要获取的课程ID（非Course Code）")
    is_major: bool = Field(title="是否获取主修可选课程")

    class Config:
        title = "获取可选具体课程信息请求值"


class _FetchEnrollCourseItemResponse(BaseModel):
    enroll_course_items: List[EnrollCourseItem] = Field(title="可选课程信息")

    class Config:
        title = "获取可选具体课程信息回传值"


@edu_admin_center_blueprint.post(uri='fetchEnrollCourseItem')
@api_request(json=_FetchEnrollCourseItemRequest)
@api_response(_FetchEnrollCourseItemResponse)
@authorized(include=[LoginApplyType.IOS_APP], need_user=True)
@handle_grpc_error
async def fetch_enroll_course_item(request: Request, body: _FetchEnrollCourseItemRequest, user: AuthorizedUser, grpc_manager: gRPCManager):
    """
    可选课程信息查询

    **仅支持IOS客户端调用**
    """
    async with grpc_manager.get_stub(ServiceEnum.EduAdminCenter) as stub:
        stub: eac_grpc.EduAdminCenterStub = stub
        res: mycqu_rr.FetchEnrollCourseItemResponse = await stub.FetchEnrollCourseItem(
            mycqu_rr.FetchEnrollCourseItemRequest(
                base_login_info=mycqu_rr.BaseLoginInfo(auth=user.username, password=user.password),
                id=body.id,
                is_major=body.is_major
            )
        )
        return _FetchEnrollCourseItemResponse.parse_obj(_message_to_dict(res))


class _FetchExamRequest(BaseModel):
    sid: str = Field(title="学号")

    class Config:
        title = "考表获取请求值"


class _FetchExamResponse(BaseModel):
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


class _FetchCourseTimetableRequest(BaseModel):
    code: str = Field(title="学/工号")
    offset: int = Field(title="学期偏移量", description="为0表示本学期，1表示下学期，应小于等于1")


class _FetchCourseTimetableResponse(BaseModel):
    timetables: List[CourseTimetable] = Field(title="课表信息")
    start_date: str = Field(title="学期起始日期，'yyyy-mm-dd'格式")
    end_date: str = Field(title="学期结束日期，'yyyy-mm-dd'格式")


@edu_admin_center_blueprint.post(uri='fetchCourseTimetable')
@api_request(json=_FetchCourseTimetableRequest)
@api_response(_FetchCourseTimetableResponse)
@authorized(need_user=True)
@handle_grpc_error
async def fetch_course_timetable(request: Request, body: _FetchCourseTimetableRequest, user: AuthorizedUser, grpc_manager: gRPCManager):
    """
    课表查询
    """
    async with grpc_manager.get_stub(ServiceEnum.EduAdminCenter) as stub:
        stub: eac_grpc.EduAdminCenterStub = stub
        res: eac_models.FetchCourseTimetableResponse = await stub.FetchCourseTimetable(
            eac_models.FetchCourseTimetableRequest(
                login_info=mycqu_rr.BaseLoginInfo(auth=user.username, password=user.password),
                code=body.code,
                offset=body.offset
            )
        )
        return _FetchCourseTimetableResponse(
            timetables=list(map(lambda x: CourseTimetable.parse_obj(_message_to_dict(x)), res.course_timetables)),
            start_date=res.start_date,
            end_date=res.end_date
        )


class _FetchScoreRequest(BaseModel):
    sid: str = Field(title="学号")
    is_minor: bool = Field(title="是否获取辅修成绩")

    class Config:
        title = "成绩查询请求值"


class _FetchScoreResponse(BaseModel):
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


@edu_admin_center_blueprint.post(uri='fetchGpaRanking')
@api_request()
@api_response(GpaRanking)
@authorized(need_user=True)
@handle_grpc_error
async def fetch_gpa_ranking(request: Request, user: AuthorizedUser, grpc_manager: gRPCManager):
    """
    绩点排名查询
    """
    async with grpc_manager.get_stub(ServiceEnum.EduAdminCenter) as stub:
        stub: eac_grpc.EduAdminCenterStub = stub
        res: mycqu_model.GpaRanking = await stub.FetchGpaRanking(
            mycqu_rr.BaseLoginInfo(auth=user.username, password=user.password)
        )
        return GpaRanking.parse_obj(_message_to_dict(res))
