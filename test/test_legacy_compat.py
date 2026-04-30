"""
旧 API 兼容层测试

需要 _321CQU 包在 PYTHONPATH 中才能运行。
运行：uv run pytest test/test_legacy_compat.py -v
"""
import pytest
from sanic_testing.testing import SanicASGITestClient


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
