from sanic import Sanic

from utils.Exceptions import _321CQUErrorHandler
from utils.log_config import LogConfig
from utils.SqlManager import SqlManager, SqliteManager
from api import *

app = Sanic('API_Gateway', log_config=LogConfig)
app.error_handler = _321CQUErrorHandler()

app.ext.add_dependency(SqlManager, SqliteManager)

app.blueprint(api_urls)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, dev=True, access_log=True)
