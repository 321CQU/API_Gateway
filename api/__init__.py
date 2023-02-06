from sanic import Blueprint

from .notification import *
from .authorization import *
from .edu_admin_center import *

__all__ = ['api_urls', 'authorized', 'LoginApplyType', 'TokenPayload', 'AuthorizedUser']

api_urls = Blueprint.group(notification_blueprint, authorization_blueprint, edu_admin_center_blueprint, version=1)
