from typing import Dict

from google.protobuf.message import Message
from google.protobuf.json_format import MessageToDict


__all__ = ['message_to_dict']


def message_to_dict(message: Message) -> Dict:
    return MessageToDict(message, including_default_value_fields=True, preserving_proto_field_name=True)
