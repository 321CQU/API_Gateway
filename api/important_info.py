from enum import StrEnum
from typing import List, Optional

from _321CQU.service import ServiceEnum
from _321CQU.tools import gRPCManager
from google.protobuf import empty_pb2
from micro_services_protobuf.control_center import control_center_models_pb2 as cc_models
from micro_services_protobuf.control_center import control_center_service_pb2_grpc as cc_grpc
from pydantic import BaseModel, Field
from sanic import Request, Blueprint

from api.authorization import authorized
from api.utils.ApiInterface import api_request, api_response, handle_grpc_error

__all__ = ['important_info_blueprint']

important_info_blueprint = Blueprint('ImportantInfo', url_prefix='/important_info')


class _HomepageInfo(BaseModel):
    class ImgPos(StrEnum):
        """
        图片存储位置
        """
        LOCAL = "LOCAL"  # 本地
        COS = "COS"  # 腾讯云COS

        @staticmethod
        def from_protobuf_enum(img_pos: cc_models.HomepageResponse.HomepageInfo.ImgPos):
            if img_pos == cc_models.HomepageResponse.HomepageInfo.ImgPos.COS:
                return _HomepageInfo.ImgPos.COS
            elif img_pos == cc_models.HomepageResponse.HomepageInfo.ImgPos.LOCAL:
                return _HomepageInfo.ImgPos.LOCAL

    class JumpType(StrEnum):
        """
        跳转信息
        """
        NONE = "NONE"  # 无跳转
        MD = "MD"  # Markdown
        URL = "URL"  # URL
        WECHAT_MINI_PROGRAM = "WECHAT_MINI_PROGRAM"  # 微信小程序

        @staticmethod
        def from_protobuf_enum(jump_type: cc_models.HomepageResponse.HomepageInfo.JumpType):
            if jump_type == cc_models.HomepageResponse.HomepageInfo.JumpType.NONE:
                return _HomepageInfo.JumpType.NONE
            elif jump_type == cc_models.HomepageResponse.HomepageInfo.JumpType.MD:
                return _HomepageInfo.JumpType.MD
            elif jump_type == cc_models.HomepageResponse.HomepageInfo.JumpType.URL:
                return _HomepageInfo.JumpType.URL
            elif jump_type == cc_models.HomepageResponse.HomepageInfo.JumpType.WECHAT_MINI_PROGRAM:
                return _HomepageInfo.JumpType.WECHAT_MINI_PROGRAM

    img_url: str = Field(title="图片URL，无路径前缀，如：/static/img/xxx.png")
    img_pos: ImgPos = Field(title="图片存储位置")
    jump_type: JumpType = Field(title="点击后跳转类型")
    jump_param: Optional[str] = Field(default=None, title="跳转参数，根据jump_type不同而不同")


class _HomepageResponse(BaseModel):
    homepages: List[_HomepageInfo] = Field(title="首页信息列表")


@important_info_blueprint.get(uri='homepages')
@api_request()
@api_response(_HomepageResponse)
@authorized()
@handle_grpc_error
async def get_homepage(request: Request, grpc_manager: gRPCManager):
    """
    获取首页轮播图
    """
    async with grpc_manager.get_stub(ServiceEnum.ImportantInfoService) as stub:
        stub: cc_grpc.ImportantInfoServiceStub = stub
        res: cc_models.HomepageResponse = await stub.GetHomepageInfos(empty_pb2.Empty())
        return _HomepageResponse(
            homepages=[_HomepageInfo(
                img_url=homepage.img_url, img_pos=_HomepageInfo.ImgPos.from_protobuf_enum(homepage.img_pos),
                jump_type=_HomepageInfo.JumpType.from_protobuf_enum(homepage.jump_type), jump_param=homepage.jump_param
            ) for homepage in res.homepages],
        )
