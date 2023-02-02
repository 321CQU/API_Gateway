from micro_services_protobuf.notification_center.apns_pb2 import SetUserApnsRequest, SendNotificationRequest
from micro_services_protobuf.common_pb2 import DefaultResponse

class MockApnStub:
    async def SetUserApns(self, request: SetUserApnsRequest) -> DefaultResponse:
        return DefaultResponse(status=1, msg='success')

    async def SendNotificationToUser(self, request: SendNotificationRequest) -> DefaultResponse:
        return DefaultResponse(status=1, msg='success')
