import pytest
from sanic_testing.testing import SanicASGITestClient


@pytest.mark.asyncio
async def test_set_user_apns(test_client: SanicASGITestClient):
    request, response = await test_client.post("/v1/notification/setApns", json={'sid': "test2", "apn": "123"})

    print(response.json)
    assert response.status == 200
