# coding: utf-8

'''
Events related to game data.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Union
from io import TextIOBase
import enum

from veredi.base.context import VerediContext
from veredi.data.context import (DataLoadContext,
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
#   External Events:
#    - Start with "Data"
#    - "Input" Events:
#      - DataSystem expect these from game systems to initiate a save/load.
#      - DataLoadRequest
#      - DataSaveRequest
#    - "Output" Events:
#      - DataSystem publishes these once a save/load is completed.
#      - DataLoadedEvent
#      - DataSavedEvent
#
#   Internal Events:
#     - Start with "_Data"
#     - Don't generally get publish - just internal to DataSystem.
#
# ---
# Data Event Flow:
# ---
# ┐
# └┬ Data Load Request         - Some game system or something publishes.
#  │                           - DataSystem receives.
#  │
#  └─┬ Loaded Event            - (internal)
#    │
#    └─┬ Deserialized Event    - (internal)
#      │
#      ├── Data Loaded Event   - DataSystem publishes.
#      │                       - Any system can receive.
#      │
#      ├── ...                 - Game Stuff Happens Here.
#      │
#      └── Data Save Request   - Some game system or something publishes.
#           │                  - DataSystem receives.
#        ┌──┘
#        Serialized Event      - (internal)
#      ┌─┘
#      Saved Event             - (internal)
#    ┌─┘
#    Data Saved Event          - DataSystem publishes.
# ───┘                         - Any system can receive.
# -----------------------------------------------------------------------------


class DataEvent(Event):
    ...

    # def create_args(self) -> Iterable:
    #     return ()
    #
    # def create_kwargs(self) -> Mapping[str, Any]:
    #     return {'data': self.data}


# -----------------------------------------------------------------------------
# Requests / Initiation
# -----------------------------------------------------------------------------

class DataLoadRequest(DataEvent):
    pass


class DataSaveRequest(DataEvent):
    pass


# -----------------------------------------------------------------------------
# Results / Notifications
# -----------------------------------------------------------------------------

class DataLoadedEvent(DataEvent):
    def __init__(self,
                 id:           Union[int, MonotonicId],
                 type:         Union[int, enum.Enum],
                 context:      DataLoadContext,  # or just VerediContext?
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

    # -------------------------------------------------------------------------
    # To String
    # -------------------------------------------------------------------------

    def _str_name(self, name: Optional[str] = None):
        name = name or self.__class__.__name__
        return f"{name}[id:{self.id},t:{self.type},cid:{self.component_id}]"

    def __repr_name__(self):
        return "DLdEvent"


class DataSavedEvent(DataEvent):

    # -------------------------------------------------------------------------
    # To String
    # -------------------------------------------------------------------------

    def _str_name(self, name: Optional[str] = None):
        name = name or self.__class__.__name__
        return f"{name}[id:{self.id},t:{self.type},cid:{self.component_id}]"

    def __repr_name__(self):
        return "DSdEvent"


# -----------------------------------------------------------------------------
# Repository Events
# -----------------------------------------------------------------------------

class _LoadedEvent(DataEvent):
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

    # -------------------------------------------------------------------------
    # To String
    # -------------------------------------------------------------------------

    def _str_data(self):
        return ('None'
                if not self.data else
                ('Closed Stream' if self.data.closed else 'Open Stream'))

    def _repr_data(self):
        return ('None'
                if not self.data else
                ('closed' if self.data.closed else 'open'))

    def _pretty(self):
        from veredi.logger import pretty
        return (f"{self._str_name()}:\n"
                + f"  data:  {self._str_data()}\n"
                + "  context:\n"
                + pretty.indented(self._context._pretty(), indent=4))

    def __str__(self):
        return (f"{self._str_name()}: data: {self._str_data()}, "
                f"context: {str(self._context)}")

    def __repr_name__(self):
        return "DesEvent"

    def __repr__(self):
        return (f"<{self._str_name(self.__repr_name__())}: "
                f"data: {self._repr_data()}, "
                f"context: {str(self._context)}>")


class _SavedEvent(DataEvent):
    ...


# -----------------------------------------------------------------------------
# Serdes Events
# -----------------------------------------------------------------------------

class _DeserializedEvent(DataEvent):
    def __init__(self,
                 id:      Union[int, MonotonicId],
                 type:    Union[int, enum.Enum],
                 context: DataLoadContext,  # or just VerediContext?
                 data:    list = None) -> None:
        self.set(id, type, context, data)

    def set(self,
            id:      Union[int, MonotonicId],
            type:    Union[int, enum.Enum],
            context: DataLoadContext,  # or just VerediContext?
            data:    list) -> None:
        super().set(id, type, context)
        self.data = data

    def reset(self) -> None:
        super().reset()
        self.data = None

    # -------------------------------------------------------------------------
    # To String
    # -------------------------------------------------------------------------

    def _str_data(self):
        return ('None'
                if not self.data else
                str(self.data))

    def _repr_data(self):
        return ('None'
                if not self.data else
                repr(self.data))

    def _pretty(self):
        from veredi.logger import pretty
        return (f"{self._str_name()}:\n"
                + f"  data:  {self._str_data()}\n"
                + "  context:\n"
                + pretty.indented(self._context._pretty(), indent=4))

    def __str__(self):
        return (f"{self._str_name()}: data: {self._str_data()}, "
                f"context: {str(self._context)}")

    def __repr_name__(self):
        return "DesEvent"

    def __repr__(self):
        return (f"<{self._str_name(self.__repr_name__())}: "
                f"data: {self._repr_data()}, "
                f"context: {str(self._context)}>")


class _SerializedEvent(DataEvent):
    pass
