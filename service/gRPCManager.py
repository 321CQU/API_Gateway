from contextlib import asynccontextmanager
from enum import StrEnum

from grpc.aio import insecure_channel, Channel

from utils.Settings import ConfigHandler
from utils.Singleton import singleton

from service.notification_center.proto import apns_pb2_grpc

__all__ = ['gRPCManager', 'ServiceEnum']


class ServiceEnum(StrEnum):
    NotificationCenter = 'notification_center'

    def get_stub_class(self):
        if self == ServiceEnum.NotificationCenter:
            return apns_pb2_grpc.ApnsStub


@singleton
class gRPCManager:
    def __init__(self):
        handler = ConfigHandler()
        all_options = handler.get_options('ServiceSetting')

        service_ports = list(filter(lambda x: x.endswith('_service_port'), all_options))
        self._service_ports = {}

        for port in service_ports:
            self._service_ports.update({
                port: handler.get_config("ServiceSetting", port)
            })

    @asynccontextmanager
    async def get_stub(self, service: ServiceEnum):
        target = service.get_stub_class()

        if target is not None:
            port = self._service_ports[service.value + "_service_port"]
            target_url = "localhost:" + port
            async with insecure_channel(target_url) as channel:
                yield target(channel)


if __name__ == '__main__':
    import logging
    import asyncio
    from service.notification_center.proto import apns_pb2
    from api.utils.ApiInterface import handle_grpc_error


    @handle_grpc_error
    async def test():
        async with gRPCManager().get_stub(ServiceEnum.NotificationCenter) as stub:
            stub: apns_pb2_grpc.ApnsStub = stub
            res = await stub.SetUserApns(apns_pb2.SetUserApnsRequest(sid="test1", apn="test"))
            print(res)


    logging.basicConfig(level=logging.INFO)
    asyncio.get_event_loop().run_until_complete(test())
