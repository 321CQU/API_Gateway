import asyncio
import inspect
import json
from functools import cache, wraps

from sanic import Request, Blueprint
from sanic.log import error_logger
from sanic.response import json as json_response, HTTPResponse

from grpc.aio import AioRpcError

from _321CQU.service import ServiceEnum
from _321CQU.tools import gRPCManager

import micro_services_protobuf.edu_admin_center.eac_models_pb2 as eac_models
import micro_services_protobuf.edu_admin_center.eac_service_pb2_grpc as eac_grpc
import micro_services_protobuf.mycqu_service.mycqu_model_pb2 as mycqu_model
import micro_services_protobuf.mycqu_service.mycqu_request_response_pb2 as mycqu_rr
import micro_services_protobuf.mycqu_service.mycqu_service_pb2_grpc as mycqu_grpc
import micro_services_protobuf.course_score_query.model_pb2 as csq_model
import micro_services_protobuf.course_score_query.service_pb2_grpc as csq_grpc
import micro_services_protobuf.notification_center.service_pb2_grpc as notification_grpc
import micro_services_protobuf.notification_center.event_pb2 as event_pb2
from micro_services_protobuf.control_center import control_center_models_pb2 as cc_models
from micro_services_protobuf.control_center import control_center_service_pb2_grpc as cc_grpc
from google.protobuf import empty_pb2
from micro_services_protobuf.common_pb2 import DefaultResponse

from .authorization import AuthorizedUser
from .utils.tools import message_to_dict
from utils.Exceptions import _321CQUException
from utils.Settings import ConfigManager

__all__ = ['legacy_compat_blueprint']

legacy_compat_blueprint = Blueprint('LegacyCompat', url_prefix='/321CQU')

LEGACY_BODY = "legacy_body"
LEGACY_VERSION = "legacy_version"


@cache
def _get_legacy_key() -> str:
    return ConfigManager().get_config('ApiKey', 'legacy_key')


def legacy_error(code: int, info: str, status_code: int = 200) -> HTTPResponse:
    return json_response(
        {"Statue": 0, "ErrorCode": code, "ErrorInfo": info},
        status=status_code,
    )


def legacy_auth(*, need_user: bool = False):
    """旧版 API Key 校验 + 参数提取装饰器

    1. 校验请求体中的 Key 字段
    2. 根据 Version 提取参数（v1.0 扁平，v2.0+ 从 Params 中提取）
    3. 若 need_user=True，提取 UserName/Password 构造 AuthorizedUser
    """

    def decorator(f):
        @wraps(f)
        async def decorated(request: Request, *args, **kwargs):
            body = request.json
            if not body:
                return legacy_error(1, "请求参数错误")

            if body.get('Key') != _get_legacy_key():
                return legacy_error(0, "Uncorrected Key")

            version = body.get('Version', '1.0')

            if version == '1.0':
                params = {k: v for k, v in body.items()
                          if k not in ('Key', 'Version')}
            else:
                params = body.get('Params', {})

            kwargs[LEGACY_BODY] = params
            kwargs[LEGACY_VERSION] = version
            request.ctx.legacy_version = version

            if need_user:
                username = params.get('UserName')
                password = params.get('Password')
                if not username or not password:
                    return legacy_error(1, "缺少 UserName/Password")
                kwargs['user'] = AuthorizedUser(
                    username=username, password=password)

            retval = f(request, *args, **kwargs)
            if inspect.isawaitable(retval):
                retval = await retval
            return retval

        return decorated

    return decorator


def legacy_response(f):
    """旧版响应格式封装装饰器

    1. 捕获异常并转为旧格式错误
    2. 正常返回值根据版本封装为旧格式
    """

    @wraps(f)
    async def decorated(request: Request, *args, **kwargs):
        try:
            retval = f(request, *args, **kwargs)
            if inspect.isawaitable(retval):
                retval = await retval

            if isinstance(retval, HTTPResponse):
                return retval

            version = getattr(request.ctx, 'legacy_version', '1.0')

            if not isinstance(retval, dict):
                return retval

            if float(version) >= 2.0:
                return json_response({"Statue": 1, "data": retval})
            else:
                return json_response({"Statue": 1, **retval})

        except _321CQUException as e:
            error_code = e.extra.get('ErrorCode', 1) if isinstance(e.extra, dict) else 1
            return legacy_error(error_code, e.error_info or str(e))
        except AioRpcError as e:
            return legacy_error(2, f"服务调用异常: {e.details()}")
        except Exception as e:
            error_logger.exception("Legacy compat 未预期错误")
            return legacy_error(1, f"服务器内部错误: {str(e)}")

    return decorated



def _session_name(session: dict) -> str:
    year = session.get('year', '')
    is_autumn = session.get('is_autumn', False)
    return f"{year}{'秋' if is_autumn else '春'}"


# ============================================================
# 组 D — 禁用端点（在其他路由之前定义，避免被通配匹配）
# ============================================================

@legacy_compat_blueprint.post('/user/login')
@legacy_response

@legacy_auth()
async def legacy_login(request: Request, legacy_body: dict, legacy_version: str):

    raise _321CQUException(error_info="Not support yet",
                           extra={'ErrorCode': 5})


@legacy_compat_blueprint.post('/school_info/get_vacant_room')
@legacy_response

@legacy_auth()
async def legacy_get_vacant_room(request: Request, legacy_body: dict, legacy_version: str):

    raise _321CQUException(error_info="Not Support Yet")


# ============================================================
# 组 A — 无需用户凭据
# ============================================================

@legacy_compat_blueprint.post('/school_info/get_course_list')
@legacy_response

@legacy_auth()
async def legacy_get_course_list(request: Request, legacy_body: dict, legacy_version: str,
                                 grpc_manager: gRPCManager):
    """搜索课程 — 按课程名或教师名"""

    course_name = legacy_body.get('CourseName')
    teacher_name = legacy_body.get('TeacherName')

    if not course_name and not teacher_name:
        return legacy_error(1, "Uncorrected Arguments")

    async with grpc_manager.get_stub(ServiceEnum.CourseScoreQuery) as stub:
        stub: csq_grpc.CourseScoreQueryStub
        res: csq_model.FindCourseByNameResponse = await stub.FindCourseByName(
            csq_model.FindCourseByNameRequest(
                teacher_name=teacher_name,
                course_name=course_name,
            )
        )

    courses = message_to_dict(res).get('courses', [])
    # 旧格式：按课程名搜索返回 [[Cid, Cname], ...]，按教师名搜索返回 [[Tname, Cid, Cname], ...]
    if course_name:
        result = [[c.get('code', ''), c.get('name', '')] for c in courses]
    else:
        result = [[c.get('instructor', ''), c.get('code', ''), c.get('name', '')] for c in courses]
    return {'Courses': result}


@legacy_compat_blueprint.post('/school_info/get_course_detail')
@legacy_response

@legacy_auth()
async def legacy_get_course_detail(request: Request, legacy_body: dict, legacy_version: str,
                                    grpc_manager: gRPCManager):
    """课程详情/历年成绩"""

    cid = legacy_body.get('Cid')
    if not cid:
        return legacy_error(1, "缺少 Cid 参数")

    async with grpc_manager.get_stub(ServiceEnum.CourseScoreQuery) as stub:
        stub: csq_grpc.CourseScoreQueryStub
        res: csq_model.FetchLayeredScoreDetailResponse = await stub.FetchLayeredScoreDetail(
            csq_model.FetchLayeredScoreDetailRequest(course_code=cid)
        )

    data = message_to_dict(res)
    score_details = data.get('score_details', [])
    course_name = data.get('course_name', '')

    if legacy_version == '1.0':
        course_score = {}
        is_hierarchy = {}
        for detail in score_details:
            tname = detail.get('teacher_name', '')
            for term_detail in detail.get('details', []):
                term = _session_name(term_detail.get('term', {}))
                info = {
                    'Tname': tname,
                    'Cname': course_name,
                    'Average': term_detail.get('average', -1),
                    'Num': term_detail.get('num', 0),
                    'Max': term_detail.get('max', -1),
                    'Min': term_detail.get('min', -1),
                    'CountNum': [
                        term_detail.get('level1_num', 0),
                        term_detail.get('level2_num', 0),
                        term_detail.get('level3_num', 0),
                        term_detail.get('level4_num', 0),
                        term_detail.get('level5_num', 0),
                    ],
                    'IsHierarchy': term_detail.get('is_hierarchy', False),
                }
                if term not in course_score:
                    course_score[term] = []
                course_score[term].append(info)
                is_hierarchy[term] = int(term_detail.get('is_hierarchy', False))
        result = {'CourseScore': course_score, 'IsHierarchy': is_hierarchy}
    else:
        course_score = []
        for detail in score_details:
            tname = detail.get('teacher_name', '')
            for term_detail in detail.get('details', []):
                term = _session_name(term_detail.get('term', {}))
                course_score.append({
                    'Term': term,
                    'Tname': tname,
                    'Cname': course_name,
                    'Average': term_detail.get('average', -1),
                    'Num': term_detail.get('num', 0),
                    'Max': term_detail.get('max', -1),
                    'Min': term_detail.get('min', -1),
                    'CountNum': [
                        term_detail.get('level1_num', 0),
                        term_detail.get('level2_num', 0),
                        term_detail.get('level3_num', 0),
                        term_detail.get('level4_num', 0),
                        term_detail.get('level5_num', 0),
                    ],
                    'IsHierarchy': term_detail.get('is_hierarchy', False),
                })
        result = {'CourseScore': course_score}
    return result


# ============================================================
# 组 B — 需要用户凭据，无版本分支
# ============================================================

@legacy_compat_blueprint.post('/student/StuVal')
@legacy_response

@legacy_auth(need_user=True)
async def legacy_stu_val(request: Request, user: AuthorizedUser, legacy_body: dict,
                         legacy_version: str, grpc_manager: gRPCManager):
    """账号验证"""

    async with grpc_manager.get_stub(ServiceEnum.EduAdminCenter) as stub:
        stub: eac_grpc.EduAdminCenterStub = stub
        res: eac_models.ValidateAuthResponse = await stub.ValidateAuth(
            mycqu_rr.BaseLoginInfo(auth=user.username, password=user.password)
        )
    return {'Sid': res.sid, 'Name': res.name}


@legacy_compat_blueprint.post('/student/get_exam')
@legacy_response

@legacy_auth(need_user=True)
async def legacy_get_exam(request: Request, user: AuthorizedUser, legacy_body: dict,
                          legacy_version: str, grpc_manager: gRPCManager):
    """考试安排"""

    sid = legacy_body.get('Sid', '')
    async with grpc_manager.get_stub(ServiceEnum.EduAdminCenter) as stub:
        stub: eac_grpc.EduAdminCenterStub = stub
        res: mycqu_rr.FetchExamResponse = await stub.FetchExam(
            mycqu_rr.FetchExamRequest(
                base_login_info=mycqu_rr.BaseLoginInfo(
                    auth=user.username, password=user.password),
                stu_id=sid,
            )
        )
    exams_data = message_to_dict(res).get('exams', [])
    return {'Exams': [{
        'RoomName': e.get('room', ''),
        'StartTime': str(e.get('start_time', '')),
        'EndTime': str(e.get('end_time', '')),
        'CourseName': e.get('course', {}).get('name', ''),
        'CourseId': e.get('course', {}).get('code', ''),
        'ExamDate': str(e.get('date', '')),
        'SeatNum': e.get('seat_num', 0),
    } for e in exams_data]}


@legacy_compat_blueprint.post('/student/get_enroll_list')
@legacy_response

@legacy_auth(need_user=True)
async def legacy_get_enroll_list(request: Request, user: AuthorizedUser, legacy_body: dict,
                                 legacy_version: str, grpc_manager: gRPCManager):
    """可选课程列表（仅 v2.0）"""

    is_major = legacy_body.get('IsMajor', True)
    async with grpc_manager.get_stub(ServiceEnum.EduAdminCenter) as stub:
        stub: eac_grpc.EduAdminCenterStub = stub
        res: mycqu_rr.FetchEnrollCourseInfoResponse = await stub.FetchEnrollCourseInfo(
            mycqu_rr.FetchEnrollCourseInfoRequest(
                base_login_info=mycqu_rr.BaseLoginInfo(
                    auth=user.username, password=user.password),
                is_major=is_major,
            )
        )
    result = {}
    for k, v in res.result.items():
        result[k] = [{
            'Id': item.id,
            'Course': {
                'CourseCode': item.course.code,
                'CourseName': item.course.name,
                'Credit': item.course.credit,
            },
            'Category': item.category,
            'EnrollSign': item.enroll_sign,
            'CourseNature': item.course_nature,
            'Campus': item.campus,
        } for item in v.info]
    return {'EnrollCourses': result}


@legacy_compat_blueprint.post('/student/get_enroll_detail')
@legacy_response

@legacy_auth(need_user=True)
async def legacy_get_enroll_detail(request: Request, user: AuthorizedUser, legacy_body: dict,
                                   legacy_version: str, grpc_manager: gRPCManager):
    """可选课程详情（仅 v2.0）"""

    enroll_id = legacy_body.get('Id', '')
    is_major = legacy_body.get('IsMajor', True)
    async with grpc_manager.get_stub(ServiceEnum.EduAdminCenter) as stub:
        stub: eac_grpc.EduAdminCenterStub = stub
        res: mycqu_rr.FetchEnrollCourseItemResponse = await stub.FetchEnrollCourseItem(
            mycqu_rr.FetchEnrollCourseItemRequest(
                base_login_info=mycqu_rr.BaseLoginInfo(
                    auth=user.username, password=user.password),
                id=enroll_id,
                is_major=is_major,
            )
        )
    items_data = message_to_dict(res).get('enroll_course_items', [])
    items = [{
        'Id': item.get('id', ''),
        'HasSelected': item.get('has_selected', False),
        'Course': {
            'CourseCode': item.get('course', {}).get('code', ''),
            'CourseName': item.get('course', {}).get('name', ''),
            'Credit': item.get('course', {}).get('credit', 0.0),
            'CourseNum': item.get('course', {}).get('course_num', ''),
            'InstructorName': item.get('course', {}).get('instructor', ''),
        },
        'Type': item.get('type_', ''),
        'SelectedNum': item.get('selected_num', 0),
        'Capacity': item.get('capacity', 0),
        'Children': item.get('children', []),
        'Campus': item.get('campus', ''),
        'Timetable': [{
            'Weeks': t.get('weeks', []),
            'Time': {
                'WeekDay': t.get('day_time', {}).get('weekday', 0),
                'Period': t.get('day_time', {}).get('period', 0),
            },
            'Pos': t.get('classroom', ''),
        } for t in item.get('timetable', [])],
    } for item in items_data]
    return {'CourseDetail': items}


@legacy_compat_blueprint.post('/library/get_borrow_list')
@legacy_response

@legacy_auth(need_user=True)
async def legacy_get_borrow_list(request: Request, user: AuthorizedUser, legacy_body: dict,
                                 legacy_version: str, grpc_manager: gRPCManager):
    """借阅列表"""

    is_curr = legacy_body.get('IsCurr', True)
    async with grpc_manager.get_stub(ServiceEnum.LibraryService) as stub:
        stub: mycqu_grpc.LibraryFetcherStub = stub
        res: mycqu_rr.FetchBorrowBookResponse = await stub.FetchBorrowBook(
            mycqu_rr.FetchBorrowBookRequest(
                info=mycqu_rr.BaseLoginInfo(
                    auth=user.username, password=user.password),
                is_curr=is_curr,
            )
        )
    books = message_to_dict(res).get('book_infos', [])
    return {'BookList': [{
        'Id': str(b.get('id', '')),
        'Title': b.get('title', ''),
        'CallNo': b.get('call_no', ''),
        'BorrowTime': b.get('borrow_time', ''),
        'ShouldReturnTime': b.get('should_return_time', ''),
        'ReturnTime': b.get('return_time', ''),
        'LibraryName': b.get('library_name', ''),
        'RenewFlag': b.get('renew_flag', False),
        'RenewCount': b.get('renew_count', 0),
        'IsReturn': b.get('is_return', False),
    } for b in books]}


@legacy_compat_blueprint.post('/library/renew_book')
@legacy_response

@legacy_auth(need_user=True)
async def legacy_renew_book(request: Request, user: AuthorizedUser, legacy_body: dict,
                            legacy_version: str, grpc_manager: gRPCManager):
    """续借书籍"""

    book_id = legacy_body.get('BookId', '')
    async with grpc_manager.get_stub(ServiceEnum.LibraryService) as stub:
        stub: mycqu_grpc.LibraryFetcherStub = stub
        res: mycqu_rr.RenewBookResponse = await stub.RenewBook(
            mycqu_rr.RenewBookRequest(
                info=mycqu_rr.BaseLoginInfo(
                    auth=user.username, password=user.password),
                book_id=book_id,
            )
        )
    if res.message != "success":
        raise _321CQUException(error_info=f"续借失败: {res.message}")
    return {'Info': res.message}


@legacy_compat_blueprint.post('/school_info/get_card')
@legacy_response

@legacy_auth(need_user=True)
async def legacy_get_card(request: Request, user: AuthorizedUser, legacy_body: dict,
                          legacy_version: str, grpc_manager: gRPCManager):
    """校园卡信息"""

    async with grpc_manager.get_stub(ServiceEnum.CardService) as stub:
        stub: mycqu_grpc.CardFetcherStub
        res: mycqu_model.Card = await stub.FetchCard(
            mycqu_rr.BaseLoginInfo(auth=user.username, password=user.password)
        )
    card_data = message_to_dict(res)
    return {'amount': card_data.get('amount', 0), 'id': card_data.get('id', '')}


@legacy_compat_blueprint.post('/school_info/get_fees')
@legacy_response

@legacy_auth(need_user=True)
async def legacy_get_fees(request: Request, user: AuthorizedUser, legacy_body: dict,
                          legacy_version: str, grpc_manager: gRPCManager):
    """水电费 / 账单"""

    is_huxi = legacy_body.get('IsHuXi', True)
    room = legacy_body.get('Room', '')
    async with grpc_manager.get_stub(ServiceEnum.CardService) as stub:
        stub: mycqu_grpc.CardFetcherStub
        res: mycqu_model.EnergyFees = await stub.FetchEnergyFee(
            mycqu_rr.FetchEnergyFeeRequest(
                base_login_info=mycqu_rr.BaseLoginInfo(
                    auth=user.username, password=user.password),
                is_hu_xi=is_huxi,
                room=room,
            )
        )
    fees_data = message_to_dict(res)
    if is_huxi:
        return {'FeesInfo': {
            'Amount': fees_data.get('amount', 0.0),
            'Eamount': fees_data.get('eamount', ''),
            'Wamount': fees_data.get('wamount', ''),
        }}
    else:
        return {'FeesInfo': {
            'Amount': fees_data.get('amount', 0.0),
            'Subsidies': fees_data.get('subsidies', ''),
        }}


@legacy_compat_blueprint.post('/homepage')
@legacy_response

@legacy_auth()
async def legacy_homepage(request: Request, legacy_body: dict, legacy_version: str,
                          grpc_manager: gRPCManager):
    """首页轮播图"""

    async with grpc_manager.get_stub(ServiceEnum.ImportantInfoService) as stub:
        stub: cc_grpc.ImportantInfoServiceStub = stub
        res: cc_models.HomepageResponse = await stub.GetHomepageInfos(empty_pb2.Empty())
    homepages = []
    for hp in res.homepages:
        homepages.append({
            'ImgUrl': hp.img_url,
            'ImgPos': hp.img_pos,
            'JumpType': hp.jump_type,
            'JumpParam': hp.jump_param,
        })
    return {'HomePages': homepages}


@legacy_compat_blueprint.post('/message/subscribe')
@legacy_response

@legacy_auth(need_user=True)
async def legacy_subscribe_message(request: Request, user: AuthorizedUser, legacy_body: dict,
                                   legacy_version: str, grpc_manager: gRPCManager):
    """消息订阅"""

    uid = legacy_body.get('Sid', '')
    code = legacy_body.get('Code', '')
    event = legacy_body.get('Event', 0)

    async with grpc_manager.get_stub(ServiceEnum.NotificationService) as stub:
        stub: notification_grpc.NotificationStub = stub
        res: DefaultResponse = await stub.UpdateEventSubscribe(
            event_pb2.UpdateEventSubscribeRequest(
                uid=bytes.fromhex(uid) if uid else b'',
                event=event,
                is_subscribe=True,
                extra_data=event_pb2.UpdateEventSubscribeRequest.ExtraData(
                    auth=user.username,
                    password=user.password,
                    extra_data=json.dumps({'Code': code}) if code else None,
                )
            )
        )
    if res.msg != 'success':
        raise _321CQUException(error_info=res.msg)
    return {}


# ============================================================
# 组 C — 需要用户凭据，有版本分支
# ============================================================

@legacy_compat_blueprint.post('/student/get_score')
@legacy_response

@legacy_auth(need_user=True)
async def legacy_get_score(request: Request, user: AuthorizedUser, legacy_body: dict,
                           legacy_version: str, grpc_manager: gRPCManager):
    """成绩查询（v1.0/v2.0 格式不同）"""

    sid = legacy_body.get('Sid', '')

    async def _fetch(grpc_manager, user, sid, is_minor):
        async with grpc_manager.get_stub(ServiceEnum.EduAdminCenter) as stub:
            stub: eac_grpc.EduAdminCenterStub = stub
            res: mycqu_rr.FetchScoreResponse = await stub.FetchScore(
                eac_models.FetchScoreRequest(
                    base_login_info=mycqu_rr.BaseLoginInfo(
                        auth=user.username, password=user.password),
                    sid=sid,
                    is_minor=is_minor,
                )
            )
        return message_to_dict(res).get('scores', [])

    major_scores, minor_scores = await asyncio.gather(
        _fetch(grpc_manager, user, sid, False),
        _fetch(grpc_manager, user, sid, True),
    )

    def _score_to_old(s):
        course = s.get('course', {})
        return {
            'CourseName': course.get('name', ''),
            'CourseCode': course.get('code', ''),
            'CourseCredit': course.get('credit', 0.0),
            'EffectiveScoreShow': s.get('score', ''),
            'StudyNature': s.get('study_nature', ''),
            'InstructorName': course.get('instructor', ''),
            'CourseNature': s.get('course_nature', ''),
        }

    if legacy_version == '1.0':
        score_log = {}
        for s in major_scores:
            term = _session_name(s.get('session', {}))
            if term not in score_log:
                score_log[term] = []
            score_log[term].append(_score_to_old(s))
        for s in minor_scores:
            term = _session_name(s.get('session', {}))
            if term not in score_log:
                score_log[term] = []
            score_log[term].append(_score_to_old(s))
        return {'ScoreLog': score_log}
    else:
        major_log = {}
        for s in major_scores:
            term = _session_name(s.get('session', {}))
            if term not in major_log:
                major_log[term] = []
            major_log[term].append(_score_to_old(s))
        minor_log = {}
        for s in minor_scores:
            term = _session_name(s.get('session', {}))
            if term not in minor_log:
                minor_log[term] = []
            minor_log[term].append(_score_to_old(s))
        return {'ScoreLog': {'主修': major_log, '辅修': minor_log}}


@legacy_compat_blueprint.post('/student/get_course')
@legacy_response

@legacy_auth(need_user=True)
async def legacy_get_course(request: Request, user: AuthorizedUser, legacy_body: dict,
                            legacy_version: str, grpc_manager: gRPCManager):
    """课表查询（v1.0/v2.0 字段名不同）"""

    code = legacy_body.get('Sid', '')
    offset = legacy_body.get('Offset', 0)
    async with grpc_manager.get_stub(ServiceEnum.EduAdminCenter) as stub:
        stub: eac_grpc.EduAdminCenterStub = stub
        res: eac_models.FetchCourseTimetableResponse = await stub.FetchCourseTimetable(
            eac_models.FetchCourseTimetableRequest(
                login_info=mycqu_rr.BaseLoginInfo(
                    auth=user.username, password=user.password),
                code=code,
                offset=offset,
            )
        )
    timetables = []
    for t in res.course_timetables:
        if legacy_version == '1.0':
            timetables.append({
                'WeekDayFormat': str(t.weekday),
                'CourseName': t.course_name,
                'CourseCode': t.course_code,
                'ClassNbr': t.course_num,
                'RoomName': t.room_name,
                'InstructorName': t.instructor_name,
                'TeachingWeekFormat': str(t.weeks),
                'PeriodFormat': str(t.day_time.period) if t.day_time else '',
                'Credit': t.credit,
            })
        else:
            timetables.append({
                'WeekDay': t.weekday,
                'CourseName': t.course_name,
                'CourseCode': t.course_code,
                'CourseNum': t.course_num,
                'RoomName': t.room_name,
                'InstructorName': t.instructor_name,
                'Weeks': list(t.weeks),
                'Period': t.day_time.period if t.day_time else 0,
                'Credit': t.credit,
            })
    return {'Courses': timetables}


@legacy_compat_blueprint.post('/student/get_gpa_ranking')
@legacy_response

@legacy_auth(need_user=True)
async def legacy_get_gpa_ranking(request: Request, user: AuthorizedUser, legacy_body: dict,
                                 legacy_version: str, grpc_manager: gRPCManager):
    """绩点排名（v1.0/v2.0 字段名不同）"""

    async with grpc_manager.get_stub(ServiceEnum.EduAdminCenter) as stub:
        stub: eac_grpc.EduAdminCenterStub = stub
        res: mycqu_model.GpaRanking = await stub.FetchGpaRanking(
            mycqu_rr.BaseLoginInfo(auth=user.username, password=user.password)
        )
    if legacy_version == '1.0':
        return {'GpaRanking': {
            'gpa': str(res.gpa),
            'majorRanking': str(res.major_ranking),
            'gradeRanking': str(res.grade_ranking),
            'classRanking': str(res.class_ranking),
        }}
    else:
        return {'GpaRanking': {
            'GPA': res.gpa,
            'MajorRank': res.major_ranking,
            'GradeRank': res.grade_ranking,
            'ClassRank': res.class_ranking,
        }}
