import pytest
from sanic_testing.testing import SanicASGITestClient

from sanic import Sanic

from _321CQU.tools.gRPCManager import gRPCManager, MockGRPCManager

from api import api_urls
from utils.Exceptions import _321CQUErrorHandler
from utils.SqlManager import SqlManager, SqliteManager
from utils.log_config import LogConfig


@pytest.fixture(scope='package')
def app() -> Sanic:
    my_app = Sanic('API_Gateway', log_config=LogConfig)
    my_app.error_handler = _321CQUErrorHandler()

    my_app.ext.add_dependency(SqlManager, SqliteManager)
    my_app.ext.add_dependency(gRPCManager, MockGRPCManager)

    my_app.blueprint(api_urls)
    return my_app


@pytest.fixture(scope='package')
def test_client(app: Sanic) -> SanicASGITestClient:
    return SanicASGITestClient(app)
