# coding: utf-8

'''
Events related to identity.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Union, Any, MutableMapping
import enum

from veredi.base.context import VerediContext
from ...ecs.base.identity import MonotonicId, ComponentId
from ..event import DataEvent


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Base Identity Events
# -----------------------------------------------------------------------------

class IdentityEvent(DataEvent):
    # -------------------------------------------------------------------------
    # To String
    # -------------------------------------------------------------------------

    def __repr_name__(self):
        return "IdEvent"


class IdentityRequest(IdentityEvent):
    # -------------------------------------------------------------------------
    # To String
    # -------------------------------------------------------------------------

    def __repr_name__(self):
        return "IdReq"


class IdentityResult(IdentityEvent):
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

    # -------------------------------------------------------------------------
    # Identity Things
    # -------------------------------------------------------------------------

    # self.component_id

    # -------------------------------------------------------------------------
    # To String
    # -------------------------------------------------------------------------

    def __str_name__(self, name: Optional[str] = None):
        name = name or self.__class__.__name__
        return f"{name}[id:{self.id},t:{self.type},cid:{self.component_id}]"

    def __repr_name__(self):
        return "IdRes"


# -----------------------------------------------------------------------------
# Identity Events
# -----------------------------------------------------------------------------

class CodeIdentityRequest(IdentityRequest):
    '''
    Code or unit tests or something want to manually build an identity
    component from supplied data.
    '''

    def __init__(self,
                 id:      Union[int, MonotonicId],
                 type:    Union[int, enum.Enum],
                 context: VerediContext,
                 data:    MutableMapping[str, Any]) -> None:
        self.set(id, type, context, data)

    def set(self,
            id:      Union[int, MonotonicId],
            type:    Union[int, enum.Enum],
            context: VerediContext,
            data:    MutableMapping[str, Any]) -> None:
        super().set(id, type, context)
        self.data = data

    def reset(self) -> None:
        super().reset()
        self.data = None

    # -------------------------------------------------------------------------
    # To String
    # -------------------------------------------------------------------------

    def __str_name__(self, name: Optional[str] = None):
        name = name or self.__class__.__name__
        return f"{name}[id:{self.id},t:{self.type}]: {self.data}"

    def __repr_name__(self):
        return "CIdReq"


# §-TODO-§ [2020-06-11]: This maybe should be deleted as DataLoadRequest
# probably covers it?
class DataIdentityRequest(IdentityRequest):
    '''
    Identity data found while loading data - please turn it into an identity
    component.
    '''

    def __init__(self,
                 id:      Union[int, MonotonicId],
                 type:    Union[int, enum.Enum],
                 context: VerediContext,
                 data:    MutableMapping[str, Any]) -> None:
        self.set(id, type, context, data)

    def set(self,
            id:      Union[int, MonotonicId],
            type:    Union[int, enum.Enum],
            context: VerediContext,
            data:    MutableMapping[str, Any]) -> None:
        super().set(id, type, context)
        self.data = data

    def reset(self) -> None:
        super().reset()
        self.data = None

    # -------------------------------------------------------------------------
    # To String
    # -------------------------------------------------------------------------

    def __str_name__(self, name: Optional[str] = None):
        name = name or self.__class__.__name__
        return f"{name}[id:{self.id},t:{self.type}]: {self.data}"

    def __repr_name__(self):
        return "DIdReq"
