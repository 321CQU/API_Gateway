import pytest

from sanic import Sanic

from server import app as my_app

from sanic_testing.testing import SanicASGITestClient


@pytest.fixture
def app():
    return SanicASGITestClient(my_app)


@pytest.mark.asyncio
async def test_set_user_apns(app: SanicASGITestClient):
    request, response = await app.post("/api/v1/notification/set_apns", json={'sid': "test2", "apn": "123"})

    print(response.json)
    assert response.status == 200
