from typing import List

from pydantic import BaseModel, Field
from sanic import Request, Blueprint

from _321CQU.tools import gRPCManager
from _321CQU.service import ServiceEnum
import micro_services_protobuf.mycqu_service.mycqu_request_response_pb2 as mycqu_rr
import micro_services_protobuf.mycqu_service.mycqu_service_pb2_grpc as mycqu_grpc
from micro_services_protobuf.model.library import BookInfo

from .authorization import authorized, AuthorizedUser
from .utils.ApiInterface import api_request, api_response, handle_grpc_error
from .utils.tools import message_to_dict

from utils.Exceptions import _321CQUException

__all__ = ['library_blueprint']

library_blueprint = Blueprint('Library', url_prefix='/library')


class FetchBorrowBookRequest(BaseModel):
    is_curr: bool = Field(title="是否获取当前借阅列表（为false则获取历史借阅列表）")


class FetchBorrowBookResponse(BaseModel):
    book_infos: List[BookInfo] = Field(title="借阅列表")


@library_blueprint.get("/borrow")
@api_request(query=FetchBorrowBookRequest)
@api_response(FetchBorrowBookResponse)
@authorized(need_user=True)
@handle_grpc_error
async def fetch_borrow_book(request: Request, query: FetchBorrowBookRequest, user: AuthorizedUser,
                            grpc_manager: gRPCManager):
    """
    获取书籍借阅信息
    """
    async with grpc_manager.get_stub(ServiceEnum.LibraryService) as stub:
        stub: mycqu_grpc.LibraryFetcherStub
        res: mycqu_rr.FetchBorrowBookResponse = await stub.FetchBorrowBook(
            mycqu_rr.FetchBorrowBookRequest(
                info=mycqu_rr.BaseLoginInfo(auth=user.username, password=user.password),
                is_curr=query.is_curr
            )
        )
    return FetchBorrowBookResponse.parse_obj(message_to_dict(res))


class RenewBookRequest(BaseModel):
    book_id: str = Field(title="续借书籍ID")


@library_blueprint.post("/borrow")
@api_request(query=RenewBookRequest)
@api_response()
@authorized(need_user=True)
@handle_grpc_error
async def renew_book(request: Request, query: RenewBookRequest, user: AuthorizedUser, grpc_manager: gRPCManager):
    """
    续借书籍
    """
    async with grpc_manager.get_stub(ServiceEnum.LibraryService) as stub:
        stub: mycqu_grpc.LibraryFetcherStub
        res: mycqu_rr.RenewBookResponse = await stub.RenewBook(
            mycqu_rr.RenewBookRequest(
                info=mycqu_rr.BaseLoginInfo(auth=user.username, password=user.password),
                book_id=query.book_id
            )
        )

        if res.message != "success":
            raise _321CQUException(error_info="续借失败", context={"msg": res.message})
