from typing import List, Optional

import micro_services_protobuf.course_score_query.model_pb2 as csq_model
import micro_services_protobuf.course_score_query.service_pb2_grpc as csq_grpc
from _321CQU.service import ServiceEnum
from _321CQU.tools import gRPCManager
from micro_services_protobuf.model.course import Course
from micro_services_protobuf.model.cqu_session import CQUSession
from pydantic import BaseModel, Field, model_validator
from sanic import Request, Blueprint
from sanic_ext import openapi
from sanic_ext.extensions.openapi.definitions import Parameter

from .authorization import authorized
from .utils.ApiInterface import api_request, api_response, handle_grpc_error
from .utils.tools import message_to_dict

__all__ = ['course_score_query_blueprint']


course_score_query_blueprint = Blueprint('CourseScoreQuery', url_prefix='/course_score_query')


class _FindCourseByNameRequest(BaseModel):
    """
    通过关键词搜索课程请求值

    两个关键词仅有一个能生效，优先基于课程关键词进行搜索
    """
    course_name: Optional[str] = Field(default=None, title="课程名关键词")
    teacher_name: Optional[str] = Field(default=None, title="教师名关键词")

    @model_validator(mode='after')
    def check_has_at_least_one_param(self) -> '_FindCourseByNameRequest':
        if self.course_name is None and self.teacher_name is None:
            raise ValueError("至少需要一个参数")
        return self


class _FindCourseByNameResponse(BaseModel):
    """
    通过关键词搜索课程返回值
    """
    courses: List[Course]


@course_score_query_blueprint.get(uri='course')
@api_request(query=_FindCourseByNameRequest)
@api_response(_FindCourseByNameResponse)
@authorized()
@handle_grpc_error
async def find_course_by_name(request: Request, query: _FindCourseByNameRequest, grpc_manager: gRPCManager):
    """
    通过关键词搜索课程
    """
    async with grpc_manager.get_stub(ServiceEnum.CourseScoreQuery) as stub:
        stub: csq_grpc.CourseScoreQueryStub
        res: csq_model.FindCourseByNameResponse = await stub.FindCourseByName(
            csq_model.FindCourseByNameRequest(teacher_name=query.teacher_name,
                                              course_name=query.course_name))
    return _FindCourseByNameResponse.model_validate(message_to_dict(res))


class _LayeredTermScoreDetail(BaseModel):
    """该课程某一学期的成绩分布"""
    term: CQUSession = Field(title='学期')
    is_hierarchy: bool = Field(title='是否为等级制度')
    max: float = Field(title='最高成绩 (无法获取时为-1)')
    min: float = Field(title='最低成绩 (无法获取时为-1)')
    average: float = Field(title='平均成绩 (无法获取时为-1)')
    num: int = Field(title='已知成绩人数')
    level1_num: int = Field(title='等级1成绩人数 (90~100 或 优)')
    level2_num: int = Field(title='等级2成绩人数 (80~90 或 良)')
    level3_num: int = Field(title='等级3成绩人数 (70~80 或 中)')
    level4_num: int = Field(title='等级4成绩人数 (60~70 或 及格)')
    level5_num: int = Field(title='等级5成绩人数 (0~60 或 不及格)')


class _LayeredScoreDetail(BaseModel):
    """分层的课程成绩信息"""
    teacher_name: str = Field(title='教师姓名')
    details: List[_LayeredTermScoreDetail] = Field(title='该教师每学期成绩')


class _FetchLayeredScoreDetailResponse(BaseModel):
    """
    通过course id查询分级的课程往年成绩返回值
    """
    course_code: str = Field(title='课程ID')
    course_name: str = Field(title='课程名')
    score_details: List[_LayeredScoreDetail] = Field(title='分层的课程信息')


@course_score_query_blueprint.get(uri='course/<cid:str>')
@openapi.parameter(parameter=Parameter('cid', str, "path", description='课程ID'))
@api_request()
@api_response(_FetchLayeredScoreDetailResponse)
@authorized()
@handle_grpc_error
async def fetch_layered_score_detail(request: Request, cid: str, grpc_manager: gRPCManager):
    """
    通过course id查询分级的课程往年成绩
    """
    async with grpc_manager.get_stub(ServiceEnum.CourseScoreQuery) as stub:
        stub: csq_grpc.CourseScoreQueryStub
        res: csq_model.FetchLayeredScoreDetailResponse = await stub.FetchLayeredScoreDetail(
            csq_model.FetchLayeredScoreDetailRequest(course_code=cid)
        )

    return _FetchLayeredScoreDetailResponse(
        course_code=res.course_code, course_name=res.course_name,
        score_details=list(map(lambda x: _LayeredScoreDetail.model_validate(message_to_dict(x)), res.score_details))
    )
