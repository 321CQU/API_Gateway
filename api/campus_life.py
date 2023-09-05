from typing import List

import micro_services_protobuf.mycqu_service.mycqu_model_pb2 as mycqu_model
import micro_services_protobuf.mycqu_service.mycqu_request_response_pb2 as mycqu_rr
import micro_services_protobuf.mycqu_service.mycqu_service_pb2_grpc as mycqu_grpc
from _321CQU.service import ServiceEnum
from _321CQU.tools import gRPCManager
from micro_services_protobuf.model.card import Card, Bill, EnergyFees
from pydantic import BaseModel, Field
from sanic import Request, Blueprint

from .authorization import authorized, AuthorizedUser
from .utils.ApiInterface import api_request, api_response, handle_grpc_error
from .utils.tools import message_to_dict

__all__ = ['campus_life_blueprint']

campus_life_blueprint = Blueprint('CampusLift', url_prefix='/campus_lift')


@campus_life_blueprint.get(uri='card')
@api_request()
@api_response(Card)
@authorized(need_user=True)
@handle_grpc_error
async def fetch_card(request: Request, user: AuthorizedUser, grpc_manager: gRPCManager):
    """
    获取校园卡信息
    """
    async with grpc_manager.get_stub(ServiceEnum.CardService) as stub:
        stub: mycqu_grpc.CardFetcherStub
        res: mycqu_model.Card = await stub.FetchCard(mycqu_rr.BaseLoginInfo(auth=user.username, password=user.password))

    return Card.model_validate(message_to_dict(res))


class FetchBillsResponse(BaseModel):
    """获取账单信息回传值"""
    bills: List[Bill] = Field(title="最近30天的账单信息")


@campus_life_blueprint.get(uri='bill/card')
@api_request()
@api_response(FetchBillsResponse)
@authorized(need_user=True)
@handle_grpc_error
async def fetch_bill(request: Request, user: AuthorizedUser, grpc_manager: gRPCManager):
    """
    获取最近30天的账单信息
    """
    async with grpc_manager.get_stub(ServiceEnum.CardService) as stub:
        stub: mycqu_grpc.CardFetcherStub
        res: mycqu_rr.FetchBillResponse = await stub.FetchBills(mycqu_rr.BaseLoginInfo(auth=user.username,
                                                                                       password=user.password))
    return FetchBillsResponse.model_validate(message_to_dict(res))


class FetchDormEnergyRequest(BaseModel):
    """获取水电费信息请求值"""
    is_huxi: bool = Field(title="是否为虎溪校区")
    room: str = Field(title="宿舍代码")


@campus_life_blueprint.get(uri='bill/dorm_energy')
@api_request(query=FetchDormEnergyRequest)
@api_response(EnergyFees)
@authorized(need_user=True)
@handle_grpc_error
async def fetch_dorm_energy(request: Request, query: FetchDormEnergyRequest,
                            user: AuthorizedUser, grpc_manager: gRPCManager):
    """
    获取宿舍水电费信息
    """
    async with grpc_manager.get_stub(ServiceEnum.CardService) as stub:
        stub: mycqu_grpc.CardFetcherStub
        res: mycqu_model.EnergyFees = await stub.FetchEnergyFee(
            mycqu_rr.FetchEnergyFeeRequest(
                base_login_info=mycqu_rr.BaseLoginInfo(auth=user.username, password=user.password),
                is_hu_xi=query.is_huxi,
                room=query.room
            )
        )
    return EnergyFees.model_validate(message_to_dict(res))
