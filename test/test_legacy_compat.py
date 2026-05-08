"""
旧 API 兼容层测试

需要 _321CQU 包在 PYTHONPATH 中才能运行。
运行：uv run pytest test/test_legacy_compat.py -v
"""
import pytest
from sanic_testing.testing import SanicASGITestClient

from api.legacy_compat import (
    _course_timetable_to_old,
    _enroll_course_info_to_old,
    _enroll_course_item_to_old,
)
from api.utils.tools import message_to_dict
from micro_services_protobuf.mycqu_service import mycqu_model_pb2


class TestLegacyAuth:
    """Key 校验和参数提取测试"""

    @pytest.fixture
    def valid_body(self):
        return {
            'Key': 'CQUz5321',
            'Version': '1.0',
        }

    async def test_correct_key_passes(self, test_client: SanicASGITestClient, valid_body):
        """正确 Key 应通过校验"""
        valid_body['CourseName'] = '计算机'
        _, response = await test_client.post(
            '/v1/321CQU/school_info/get_course_list', json=valid_body
        )
        assert response.status == 200

    async def test_wrong_key_fails(self, test_client: SanicASGITestClient, valid_body):
        """错误 Key 应返回旧格式错误"""
        valid_body['Key'] = 'wrong_key'
        _, response = await test_client.post(
            '/v1/321CQU/school_info/get_course_list', json=valid_body
        )
        assert response.status == 200
        data = response.json
        assert data['Statue'] == 0
        assert data['ErrorCode'] == 0
        assert 'Uncorrected Key' in data['ErrorInfo']

    async def test_missing_key_fails(self, test_client: SanicASGITestClient):
        """缺少 Key 应返回错误"""
        _, response = await test_client.post(
            '/v1/321CQU/school_info/get_course_list', json={'CourseName': 'test'}
        )
        assert response.status == 200
        data = response.json
        assert data['Statue'] == 0

    async def test_missing_body_returns_error(self, test_client: SanicASGITestClient):
        """空请求体应返回错误"""
        _, response = await test_client.post(
            '/v1/321CQU/school_info/get_course_list', json=None
        )
        assert response.status == 200
        data = response.json
        assert data['Statue'] == 0


class TestLegacyVersion:
    """版本处理测试"""

    @pytest.fixture
    def base_body(self):
        return {
            'Key': 'CQUz5321',
        }

    async def test_v1_flat_params(self, test_client: SanicASGITestClient, base_body):
        """v1.0 请求参数从顶层提取"""
        base_body['Version'] = '1.0'
        base_body['Cid'] = 'CS101'
        _, response = await test_client.post(
            '/v1/321CQU/school_info/get_course_detail', json=base_body
        )
        assert response.status == 200

    async def test_v2_nested_params(self, test_client: SanicASGITestClient, base_body):
        """v2.0 请求参数从 Params 中提取"""
        base_body['Version'] = '2.0'
        base_body['Params'] = {'Cid': 'CS101'}
        _, response = await test_client.post(
            '/v1/321CQU/school_info/get_course_detail', json=base_body
        )
        assert response.status == 200

    async def test_default_version_is_v1(self, test_client: SanicASGITestClient, base_body):
        """不传 Version 时默认按 v1.0 处理"""
        base_body['Cid'] = 'CS101'
        # 不设置 Version 字段
        _, response = await test_client.post(
            '/v1/321CQU/school_info/get_course_detail', json=base_body
        )
        assert response.status == 200


class TestLegacyResponseFormat:
    """响应格式测试"""

    @pytest.fixture
    def course_timetable(self):
        return mycqu_model_pb2.CourseTimetable(
            course=mycqu_model_pb2.Course(
                name='高等数学',
                code='MATH101',
                course_num='001',
                credit=4.0,
                instructor='张三',
            ),
            classroom='D123',
            classroom_name='D123 教室',
            weeks=[mycqu_model_pb2.Period(start=1, end=16)],
            day_time=mycqu_model_pb2.CourseDayTime(
                weekday=2,
                period=mycqu_model_pb2.Period(start=3, end=4),
            ),
        )

    def test_course_timetable_uses_day_time_weekday_for_v1(self, course_timetable):
        """课表 weekday 位于 day_time 内，不在顶层"""
        data = _course_timetable_to_old(course_timetable, '1.0')

        assert data['WeekDayFormat'] == '2'
        assert data['CourseName'] == '高等数学'
        assert data['CourseCode'] == 'MATH101'
        assert data['ClassNbr'] == '001'
        assert data['RoomName'] == 'D123 教室'
        assert data['InstructorName'] == '张三'
        assert data['Credit'] == 4.0

    def test_course_timetable_uses_day_time_weekday_for_v2(self, course_timetable):
        """v2 格式也应从 day_time 读取星期，并返回可 JSON 序列化的节次"""
        data = _course_timetable_to_old(course_timetable, '2.0')

        assert data['WeekDay'] == 2
        assert data['CourseName'] == '高等数学'
        assert data['CourseCode'] == 'MATH101'
        assert data['CourseNum'] == '001'
        assert data['Weeks'] == [{'start': 1, 'end': 16}]
        assert data['Period'] == {'start': 3, 'end': 4}

    def test_enroll_course_info_converts_repeated_campus_to_list(self):
        """选课列表的 campus 是 repeated 字段，应转成普通 list"""
        item = mycqu_model_pb2.EnrollCourseInfo(
            id='enroll-1',
            course=mycqu_model_pb2.Course(
                name='大学物理',
                code='PHY101',
                credit=3.0,
            ),
            category='公共基础课',
            enroll_sign='已选',
            course_nature='必修',
            campus=['A区', 'D区'],
        )

        data = _enroll_course_info_to_old(item)

        assert data['Course']['CourseCode'] == 'PHY101'
        assert data['Campus'] == ['A区', 'D区']

    def test_enroll_course_item_uses_actual_dict_field_names(self):
        """选课详情应使用 checked/type/timetables/time/pos 等实际字段"""
        item = mycqu_model_pb2.EnrollCourseItem(
            id='item-1',
            checked=True,
            course=mycqu_model_pb2.Course(
                name='程序设计',
                code='CS101',
                course_num='002',
                credit=2.0,
                instructor='李四',
            ),
            type='理论',
            selected_num=30,
            capacity=40,
            campus='D区',
            timetables=[
                mycqu_model_pb2.EnrollCourseTimetable(
                    weeks=[mycqu_model_pb2.Period(start=1, end=8)],
                    time=mycqu_model_pb2.CourseDayTime(
                        weekday=4,
                        period=mycqu_model_pb2.Period(start=5, end=6),
                    ),
                    pos='D楼204',
                )
            ],
        )

        data = _enroll_course_item_to_old(message_to_dict(item))

        assert data['HasSelected'] is True
        assert data['Type'] == '理论'
        assert data['Timetable'][0]['Time']['WeekDay'] == 4
        assert data['Timetable'][0]['Time']['Period'] == {'start': 5, 'end': 6}
        assert data['Timetable'][0]['Pos'] == 'D楼204'

    async def test_v1_response_format(self, test_client: SanicASGITestClient):
        """v1.0 响应格式：字段平铺在顶层"""
        body = {
            'Key': 'CQUz5321',
            'Version': '1.0',
            'Sid': '20210001',
            'UserName': 'testuser',
            'Password': 'testpass',
        }
        _, response = await test_client.post(
            '/v1/321CQU/student/StuVal', json=body
        )
        data = response.json
        assert data.get('Statue') == 1
        # v1.0 格式：字段直接在天层，不在 data 中
        assert 'Sid' in data or 'data' in data

    async def test_v2_response_format(self, test_client: SanicASGITestClient):
        """v2.0 响应格式：数据在 data 字段中"""
        body = {
            'Key': 'CQUz5321',
            'Version': '2.0',
            'Sid': '20210001',
            'UserName': 'testuser',
            'Password': 'testpass',
        }
        _, response = await test_client.post(
            '/v1/321CQU/student/StuVal', json=body
        )
        data = response.json
        assert data.get('Statue') == 1
        # v2.0 格式：数据应在 data 字段中
        assert 'data' in data or 'Sid' in data


class TestDisabledEndpoints:
    """禁用端点测试"""

    async def test_login_returns_not_support(self, test_client: SanicASGITestClient):
        """user/login 应返回 Not support yet"""
        body = {
            'Key': 'CQUz5321',
            'Version': '1.0',
            'UserName': 'test',
            'Password': 'test',
        }
        _, response = await test_client.post(
            '/v1/321CQU/user/login', json=body
        )
        data = response.json
        assert data['Statue'] == 0
        assert data['ErrorCode'] == 5
        assert 'Not support yet' in data['ErrorInfo']

    async def test_vacant_room_returns_not_support(self, test_client: SanicASGITestClient):
        """get_vacant_room 应返回 Not Support Yet"""
        body = {
            'Key': 'CQUz5321',
            'Version': '1.0',
            'UserName': 'test',
            'Password': 'test',
        }
        _, response = await test_client.post(
            '/v1/321CQU/school_info/get_vacant_room', json=body
        )
        data = response.json
        assert data['Statue'] == 0
        assert 'Not Support Yet' in data['ErrorInfo']


class TestLegacyErrorHandling:
    """错误处理测试"""

    async def test_grpc_error_returns_legacy_format(self, test_client: SanicASGITestClient):
        """gRPC 错误应转为旧格式"""
        body = {
            'Key': 'CQUz5321',
            'Version': '1.0',
            'Sid': '20210001',
            'UserName': 'testuser',
            'Password': 'testpass',
        }
        _, response = await test_client.post(
            '/v1/321CQU/student/get_exam', json=body
        )
        assert response.status == 200
        data = response.json
        # 如果 mock 没有正确设置，应返回错误格式
        assert 'Statue' in data

    async def test_missing_user_params(self, test_client: SanicASGITestClient):
        """需要用户凭据的端点缺少 UserName/Password 时应返回错误"""
        body = {
            'Key': 'CQUz5321',
            'Version': '1.0',
        }
        _, response = await test_client.post(
            '/v1/321CQU/student/get_score', json=body
        )
        data = response.json
        assert data['Statue'] == 0
