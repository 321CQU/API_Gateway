from inspect import isclass
from typing import Dict, Any, get_type_hints

from google.protobuf.message import Message
from google.protobuf.json_format import MessageToDict

__all__ = ['message_to_dict', 'component']

from sanic import SanicException

from sanic_ext.extensions.openapi.definitions import Reference, Components
from sanic_ext.utils.typing import is_pydantic


# 从sanic_ext.extensions.openapi.definition中复制过来的, 以解决pydantic v2的问题
def component(
        obj: Any, *, name: str = "", field: str = "schemas"
) -> Reference:
    hints = get_type_hints(Components)

    if field not in hints:
        raise AttributeError(
            f"Unknown field '{field}'. Must be a valid field per OAS3 "
            "requirements. See "
            "https://swagger.io/specification/#components-object."
        )

    if not isclass(obj) and not name:
        raise SanicException(
            f"Components {obj} must be created with a declared name"
        )

    if not name:
        name = obj.__name__

    from sanic_ext.extensions.openapi.builders import SpecificationBuilder

    spec = SpecificationBuilder()
    refval = f"#/components/{field}/{name}"
    ref = Reference(refval)

    if not spec.has_component(field, name):
        prop_info = hints[field]
        type_ = prop_info.__args__[1]
        if is_pydantic(obj):
            try:
                schema = obj.model_json_schema  # pydantic v2已经改用`model_json_schema`
            except AttributeError:
                schema = obj.__pydantic_model__.schema
            component = schema(ref_template="#/components/schemas/{model}")
            definitions = component.pop("$defs", None)  # pydantic v2 已经改用`$defs`而非`definitions`
            if definitions:
                for key, value in definitions.items():
                    spec.add_component(field, key, value)
        else:
            component = (
                type_.make(obj) if hasattr(type_, "make") else type_(obj)
            )

        spec.add_component(field, name, component)

    return ref


def message_to_dict(message: Message) -> Dict:
    return MessageToDict(message, including_default_value_fields=True, preserving_proto_field_name=True)
