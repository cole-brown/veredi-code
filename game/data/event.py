# coding: utf-8

'''
Events related to game data.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Union
import io
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
#      - DataManager expect these from game systems to initiate a save/load.
#      - DataLoadRequest
#      - DataSaveRequest
#    - "Output" Events:
#      - DataManager publishes these once a save/load is completed.
#      - DataLoadedEvent
#      - DataSavedEvent
#
#   Internal Events:
#     - Start with "_Data"
#     - Don't generally get publish - just internal to DataManager.
#
# ---
# Data Event Flow:
# ---
# ┐
# └┬ Data Load Request         - Some game system or something publishes.
#  │                           - DataManager receives.
#  │
#  └─┬ Loaded Event            - (internal)
#    │
#    └─┬ Deserialized Event    - (internal)
#      │
#      ├── Data Loaded Event   - DataManager publishes.
#      │                       - Any system can receive.
#      │
#      ├── ...                 - Game Stuff Happens Here.
#      │
#      └── Data Save Request   - Some game system or something publishes.
#           │                  - DataManager receives.
#        ┌──┘
#        Serialized Event      - (internal)
#      ┌─┘
#      Saved Event             - (internal)
#    ┌─┘
#    Data Saved Event          - DataManager publishes.
# ───┘                         - Any system can receive.
# -----------------------------------------------------------------------------


class DataEvent(Event):
    ...

    # def create_args(self) -> Iterable:
    #     return ()
    #
    # def create_kwargs(self) -> Mapping[str, Any]:
    #     return {'data': self._data}


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

    def __str_name__(self, name: Optional[str] = None):
        name = name or self.__class__.__name__
        return f"{name}[id:{self.id},t:{self.type},cid:{self.component_id}]"

    def __repr_name__(self):
        return "LoadEvent"


class DataSavedEvent(DataEvent):

    # -------------------------------------------------------------------------
    # To String
    # -------------------------------------------------------------------------

    def __str_name__(self, name: Optional[str] = None):
        name = name or self.__class__.__name__
        return f"{name}[id:{self.id},t:{self.type},cid:{self.component_id}]"

    def __repr_name__(self):
        return "SavedEvent"


# -----------------------------------------------------------------------------
# Repository Events
# -----------------------------------------------------------------------------

class _LoadedEvent(DataEvent):

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def __init__(self,
                 id:      Union[int, MonotonicId],
                 type:    Union[int, enum.Enum],
                 context: VerediContext,
                 data:    Optional[io.TextIOBase] = None) -> None:
        self._data: io.TextIOBase = None
        self.set(id, type, context, data)

    def set(self,
            id:      Union[int, MonotonicId],
            type:    Union[int, enum.Enum],
            context: VerediContext,
            data:    Optional[io.TextIOBase]) -> None:
        super().set(id, type, context)
        self._data = data

    def reset(self) -> None:
        super().reset()
        self._data = None

    # -------------------------------------------------------------------------
    # Data Accessors
    # -------------------------------------------------------------------------

    def data_exists(self) -> bool:
        '''
        Returns true if self._data is not none and is not zero length. Can
        return true even if data is not readable, for example: when data exists
        but stream position is at the very end of the data (so no /more/ data
        can be read).
        '''
        return (self._data
                and (self._data.readable() or
                     self._data.tell() > 0))

    def data_ready(self) -> bool:
        '''
        Returns true if self._data is not none and can currently be read from.
        Only returns true if you can read the data with no other operations.
        '''
        return self._data and self._data.readable()

    def data(self,
             seek_to: Optional[int] = None) -> Optional[str]:
        '''
        Returns data string from current position in stream to the current end
        of stream.

        Set `seek_to` to 0 if you want to be sure to read /all/ off the current
        data.

        Raises OSError if the stream `read()` call fails.
        '''
        if self._data is None:
            return None

        # Seek to elsewhere in stream?
        if seek_to is not None:
            self._data.seek(seek_to)

        # Return stream's string.
        return self._data.read(None)

    # -------------------------------------------------------------------------
    # To String
    # -------------------------------------------------------------------------

    def _str_data(self):
        return ('None'
                if not self.data_exists() else
                ('Closed Stream' if self._data.closed else 'Open Stream'))

    def _repr_data(self):
        return ('None'
                if not self.data_exists() else
                ('closed' if self._data.closed else 'open'))

    def _pretty(self):
        from veredi.logger import pretty
        return (f"{self.__str_name__()}:\n"
                + f"  data:  {self._str_data()}\n"
                + "  context:\n"
                + pretty.indented(self._context._pretty(), indent=4))

    def __str__(self):
        return (f"{self.__str_name__()}: data: {self._str_data()}, "
                f"context: {str(self._context)}")

    def __repr_name__(self):
        return "_LdEvent"

    def __repr__(self):
        return (f"<{self.__str_name__(self.__repr_name__())}: "
                f"data: {self._repr_data()}, "
                f"context: {str(self._context)}>")


class _SavedEvent(DataEvent):
    def __repr_name__(self):
        return "_SvdEvent"


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
        return (f"{self.__str_name__()}:\n"
                + f"  data:  {self._str_data()}\n"
                + "  context:\n"
                + pretty.indented(self._context._pretty(), indent=4))

    def __str__(self):
        return (f"{self.__str_name__()}: data: {self._str_data()}, "
                f"context: {str(self._context)}")

    def __repr_name__(self):
        return "_DesEvent"

    def __repr__(self):
        return (f"<{self.__str_name__(self.__repr_name__())}: "
                f"data: {self._repr_data()}, "
                f"context: {str(self._context)}>")


class _SerializedEvent(DataEvent):
    def __repr_name__(self):
        return "_SerEvent"
