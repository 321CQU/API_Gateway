from google.protobuf import any_pb2 as _any_pb2
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class DefaultResponse(_message.Message):
    __slots__ = ["data", "msg", "status"]
    DATA_FIELD_NUMBER: _ClassVar[int]
    MSG_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    data: _any_pb2.Any
    msg: str
    status: int
    def __init__(self, status: _Optional[int] = ..., msg: _Optional[str] = ..., data: _Optional[_Union[_any_pb2.Any, _Mapping]] = ...) -> None: ...

class SendNotificationRequest(_message.Message):
    __slots__ = ["notification", "sid"]
    class AppleNotification(_message.Message):
        __slots__ = ["alert", "badge", "category"]
        class AppleAlert(_message.Message):
            __slots__ = ["body", "subtitle", "title"]
            BODY_FIELD_NUMBER: _ClassVar[int]
            SUBTITLE_FIELD_NUMBER: _ClassVar[int]
            TITLE_FIELD_NUMBER: _ClassVar[int]
            body: str
            subtitle: str
            title: str
            def __init__(self, title: _Optional[str] = ..., subtitle: _Optional[str] = ..., body: _Optional[str] = ...) -> None: ...
        ALERT_FIELD_NUMBER: _ClassVar[int]
        BADGE_FIELD_NUMBER: _ClassVar[int]
        CATEGORY_FIELD_NUMBER: _ClassVar[int]
        alert: SendNotificationRequest.AppleNotification.AppleAlert
        badge: int
        category: str
        def __init__(self, alert: _Optional[_Union[SendNotificationRequest.AppleNotification.AppleAlert, _Mapping]] = ..., badge: _Optional[int] = ..., category: _Optional[str] = ...) -> None: ...
    NOTIFICATION_FIELD_NUMBER: _ClassVar[int]
    SID_FIELD_NUMBER: _ClassVar[int]
    notification: SendNotificationRequest.AppleNotification
    sid: str
    def __init__(self, sid: _Optional[str] = ..., notification: _Optional[_Union[SendNotificationRequest.AppleNotification, _Mapping]] = ...) -> None: ...

class SetUserApnsRequest(_message.Message):
    __slots__ = ["apn", "sid"]
    APN_FIELD_NUMBER: _ClassVar[int]
    SID_FIELD_NUMBER: _ClassVar[int]
    apn: str
    sid: str
    def __init__(self, sid: _Optional[str] = ..., apn: _Optional[str] = ...) -> None: ...
