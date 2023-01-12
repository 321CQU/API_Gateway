from sanic import Blueprint

from .notification import *

__all__ = ['api_urls']

api_urls = Blueprint.group(notification_blueprint, version=1, version_prefix='/api/v')
