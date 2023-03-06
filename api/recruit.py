import random
from typing import List

from pydantic import BaseModel, Field
from sanic import Request, Blueprint

from micro_services_protobuf.model.score import Score, Course
from micro_services_protobuf.model.cqu_session import CQUSession

from .authorization import authorized, LoginApplyType
from .utils.ApiInterface import api_request, api_response


__all__ = ['recruit_blueprint']

recruit_blueprint = Blueprint('Recruit', url_prefix='/recruit')


class _FetchScoreResponse(BaseModel):
    scores: List[Score] = Field(title="成绩")

    class Config:
        title = "成绩查询回传值"


@recruit_blueprint.get(uri='score')
@api_request()
@api_response(_FetchScoreResponse)
@authorized(include=[LoginApplyType.Recruit])
async def fetch_score(request: Request):
    """
    获取成绩信息
    """

    result: List[Score] = []
    for i in range(10):
        result.append(
            Score(
                session=CQUSession(year=2023, is_autumn=False),
                course=Course(
                    name=f'测试课程{i}', code=str(i), course_num=f'xxx{i}', credit=1.0,
                    instructor=f'测试教师{i}'
                ),
                score=str(random.randint(0, 100)),
                study_nature='初修',
                course_nature='必修'
            )
        )
    return _FetchScoreResponse(scores=result)

