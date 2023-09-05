import pytest
from sanic_testing.testing import SanicASGITestClient

from test import test_client
from utils.Settings import ConfigManager

_login_params = {
    'apiKey': ConfigManager().get_config('ApiKey', 'IOS_APP'), 'applyType': 'IOS_APP',
    'username': "test2", "password": "123"
}


@pytest.mark.asyncio
async def test_set_user_apns(test_client: SanicASGITestClient):
    request2, response2 = await test_client.post(
        "/v1/authorization/login",
        json=_login_params
    )

    token = response2.json["data"]["token"]

    request, response = await test_client.post("/v1/notification/setApns", json={'sid': "test2", "apn": "123"}, headers={'Authorization': 'Bearer ' + token})

    print(response.json)
    assert response.status == 200
