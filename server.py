from sanic import Sanic

from utils.Exceptions import _321CQUErrorHandler
from utils.log_config import LogConfig
from api import *

app = Sanic('API_Gateway', log_config=LogConfig)
app.error_handler = _321CQUErrorHandler()
app.blueprint(api_urls)

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8000, dev=True, access_log=True)
