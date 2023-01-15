from service.notification_center.proto.apns_pb2 import SetUserApnsRequest, SendNotificationRequest, DefaultResponse


class MockApnStub:
    async def SetUserApns(self, request: SetUserApnsRequest) -> DefaultResponse:
        return DefaultResponse(status=1, msg='success')

    async def SendNotificationToUser(self, request: SendNotificationRequest) -> DefaultResponse:
        return DefaultResponse(status=1, msg='success')
