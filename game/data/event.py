# coding: utf-8

'''
Events related to game data.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Any, Optional, Set, Type, Union
from io import TextIOBase
import enum

from veredi.base.context import (VerediContext,
                                 DataGameContext,
                                 DataLoadContext,
                                 DataSaveContext)
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


# ------------------------------------------------------------------------------
# General Data Events
# ------------------------------------------------------------------------------

class DataLoadRequest(Event):
    pass


class DataSaveRequest(Event):
    pass


class DataLoadedEvent(Event):
    pass


class DataSavedEvent(Event):
    pass


# ------------------------------------------------------------------------------
# Serialization / Repository Events
# ------------------------------------------------------------------------------

class DeserializedEvent(Event):
    def __init__(self,
                 id:      int,
                 type:    Union[int, enum.Enum],
                 context: Optional[VerediContext] = None,
                 data:    Optional[TextIOBase]    = None) -> None:
        self.set(id, type, context, data)

    def set(self,
            id:      int,
            type:    Union[int, enum.Enum],
            context: Optional[VerediContext],
            data:    Optional[TextIOBase]) -> None:
        super().set(id, type, context)
        self.data = data

    def reset(self) -> None:
        super().reset()
        self.data = None


class SerializedEvent(Event):
    pass


# ------------------------------------------------------------------------------
# Codec Events
# ------------------------------------------------------------------------------

class DecodedEvent(Event):
    def __init__(self,
                 id:      int,
                 type:    Union[int, enum.Enum],
                 context: Optional[VerediContext] = None,
                 data:    list                    = None) -> None:
        self.set(id, type, context, data)

    def set(self,
            id:      int,
            type:    Union[int, enum.Enum],
            context: Optional[VerediContext],
            data:    list) -> None:
        super().set(id, type, context)
        self.data = data

    def reset(self) -> None:
        super().reset()
        self.data = None


class EncodedEvent(Event):
    pass

