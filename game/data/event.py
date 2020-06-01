# coding: utf-8

'''
Events related to game data.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (Optional, Any, Type, Union,
                    Set, MutableMapping, Mapping, Iterable)
from io import TextIOBase
import enum

from veredi.base.context import VerediContext
from veredi.data.context import (DataGameContext,
                                 DataLoadContext,
                                 DataSaveContext)
from ..ecs.base.identity import (MonotonicId,
                                 ComponentId)
from ..ecs.event import Event


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Events
# ---
# ---
# Data Event Flow:
# ---
#  ┌ Data Load Request       - data/save owns
#  │                         - data/save pubs ?
#  │                         - Repo subs
#  └─┬ Deserialized Event    - Repo owns
#    │   - aka Load Event?
#    │                       - Repo pubs
#    │                       - Codec subs
#    └─┬ Decoded Event       - Codec owns
#      │                     - Codec pubs
#      │                     - ComponentManager subs?
#      ├── Data Loaded Event - ?
#      ├── ...
#      └─┬ Data Save Request - Repo owns ?
#        │                   - Codec owns ?
#        │                   - Codec subs
#      ┌─┴ Encoded Event     - Codec owns
#      │                     - Codec pubs
#      │                     - Repo subs
#    ┌─┴ Serialized Event    - Repo owns
#    │                       - Repo pubs
#    │                       - data/save subs
#    ├ Data Saved Event      - data/save owns
#    │                       - data/save pubs
# ------------------------------------------------------------------------------


class DataEvent(Event):
    pass

    # def create_args(self) -> Iterable:
    #     return ()
    #
    # def create_kwargs(self) -> Mapping[str, Any]:
    #     return {'data': self.data}


# ------------------------------------------------------------------------------
# General Data Events
# ------------------------------------------------------------------------------

class DataLoadRequest(DataEvent):
    pass


class DataSaveRequest(DataEvent):
    pass


class DataLoadedEvent(DataEvent):
    def __init__(self,
                 id:           Union[int, MonotonicId],
                 type:         Union[int, enum.Enum],
                 context:      VerediContext,
                 component_id: Union[int, ComponentId]) -> None:
        self.set(id, type, context, component_id)

    def set(self,
            id:           Union[int, MonotonicId],
            type:         Union[int, enum.Enum],
            context:      VerediContext,
            component_id: Union[int, ComponentId]) -> None:
        super().set(id, type, context)
        self.component_id = component_id

    def reset(self) -> None:
        super().reset()
        self.component_id = ComponentId.INVALID

class DataSavedEvent(DataEvent):
    pass


# ------------------------------------------------------------------------------
# Serialization / Repository Events
# ------------------------------------------------------------------------------

class DeserializedEvent(DataEvent):
    def __init__(self,
                 id:      Union[int, MonotonicId],
                 type:    Union[int, enum.Enum],
                 context: VerediContext,
                 data:    Optional[TextIOBase]    = None) -> None:
        self.set(id, type, context, data)

    def set(self,
            id:      Union[int, MonotonicId],
            type:    Union[int, enum.Enum],
            context: VerediContext,
            data:    Optional[TextIOBase]) -> None:
        super().set(id, type, context)
        self.data = data

    def reset(self) -> None:
        super().reset()
        self.data = None


class SerializedEvent(DataEvent):
    pass


# ------------------------------------------------------------------------------
# Codec Events
# ------------------------------------------------------------------------------

class DecodedEvent(DataEvent):
    def __init__(self,
                 id:      Union[int, MonotonicId],
                 type:    Union[int, enum.Enum],
                 context: VerediContext,
                 data:    list = None) -> None:
        self.set(id, type, context, data)

    def set(self,
            id:      Union[int, MonotonicId],
            type:    Union[int, enum.Enum],
            context: VerediContext,
            data:    list) -> None:
        super().set(id, type, context)
        self.data = data

    def reset(self) -> None:
        super().reset()
        self.data = None


class EncodedEvent(DataEvent):
    pass

