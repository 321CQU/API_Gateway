from sanic import Sanic

from _321CQU.tools.gRPCManager import gRPCManager

from utils.Exceptions import _321CQUErrorHandler
from utils.log_config import LogConfig
from utils.SqlManager import SqlManager, SqliteManager
from api import *

app = Sanic('API_Gateway', log_config=LogConfig)

app.config.CORS_ORIGINS = ["http://321cqu.com", "https://321cqu.com", "http://api.321cqu.com", "https://api.321cqu.com"]
app.config.CORS_SUPPORTS_CREDENTIALS = True

app.error_handler = _321CQUErrorHandler()

app.ext.add_dependency(SqlManager, SqliteManager)
app.ext.add_dependency(gRPCManager, lambda: gRPCManager())

app.blueprint(api_urls)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, access_log=True)
