from sanic import Sanic

from utils.logger import LogConfig

app = Sanic('API_Gateway', log_config=LogConfig)

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8000, dev=True, access_log=True)
