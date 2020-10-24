# coding: utf-8

'''
Events for Math, Maths, Mathing, Mathers, and Jeff.
'''


# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Union, NewType
import enum
from decimal import Decimal

from veredi.base.context           import VerediContext
from veredi.base.identity          import SerializableId
from veredi.game.ecs.base.identity import EntityId
from veredi.game.ecs.event         import Event
from veredi.interface.output.event import OutputEvent, Recipient

from .parser import MathTree


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

MathValueType = NewType('MathValueType', Union[int, float, Decimal])
MathValue = (int, float, Decimal)


# -----------------------------------------------------------------------------
# Base Math Event
# -----------------------------------------------------------------------------

class MathEvent(Event):
    '''
    Subclass off this or another MathEvent subclass to work with MathSystem
    on mathing stuff.
    '''

    def __init__(self,
                 id:           Union[int, EntityId],
                 type:         Union[int, enum.Enum],
                 context:      VerediContext,
                 root:         MathTree) -> None:
        self.set(id, type, context, root)

    def set(self,
            id:           Union[int, EntityId],
            type:         Union[int, enum.Enum],
            context:      VerediContext,
            root:         MathTree) -> None:
        super().set(id, type, context)
        self.root = root
        self.total = None

    def reset(self) -> None:
        super().reset()
        self.root = None
        self.total = None

    # -------------------------------------------------------------------------
    # Math System
    # -------------------------------------------------------------------------

    def finalize(self,
                 root: MathTree,
                 total: MathValueType) -> None:
        '''
        Get this event ready for publishing.
        '''
        super().reset()
        self.root = root
        self.total = total

    # -------------------------------------------------------------------------
    # To String
    # -------------------------------------------------------------------------

    def __repr_name__(self):
        return "MathEvent"

    def __str__(self):
        return (f"{self._str_name()}: "
                f"math: {self.root}, "
                f"context: {str(self._context)}")

    def __repr__(self):
        return (f"<{self._str_name(self.__repr_name__())}: "
                f"math: {repr(self.root)}, "
                f"context: {repr(self._context)}"
                ">")


# -----------------------------------------------------------------------------
# A Result!
# -----------------------------------------------------------------------------

class MathResult(MathEvent):
    '''
    Subclass off this or another MathEvent subclass to work with MathSystem
    on mathing stuff.
    '''

    # -------------------------------------------------------------------------
    # To String
    # -------------------------------------------------------------------------

    def __repr_name__(self):
        return "MathResult"


# -----------------------------------------------------------------------------
# Output to Users
# -----------------------------------------------------------------------------

class MathOutputEvent(OutputEvent):
    '''
    This math event is for directing a finalized math result towards the
    command/event output flow.

    Users will see the result soon.

    Note: Subclassed off of OutputEvent instead of MathEvent.
    '''

    # Same as OutputEvent's right now:
    # def __init__(self,
    #              source_id:     Union[int, EntityId],
    #              source_type:   Union[int, enum.Enum],
    #              output:        Optional[MathTree],
    #              context:       VerediContext,
    #              serial_id:     SerializableId,
    #              recipients: Recipient) -> None:
    #     self.set(source_id, source_type, output, context,
    #              serial_id, recipients)

    def set(self,
            source_id:     Union[int, EntityId],
            source_type:   Union[int, enum.Enum],
            output:        Optional[MathTree],
            context:       VerediContext,
            serial_id:     SerializableId,
            recipients:    Recipient) -> None:
        super().set(source_id, source_type,
                    output, context,
                    serial_id, recipients)
        # ---
        # Set/Init our vars.
        # ---
        self._total: Optional[MathValueType] = None

    def reset(self) -> None:
        super().reset()
        self._total = None

    # -------------------------------------------------------------------------
    # Output Things
    # -------------------------------------------------------------------------

    @property
    def total(self) -> Optional[MathValueType]:
        '''
        Returns the math event's total.
        '''
        return self._output

    @property
    def dotted(self):
        '''
        Veredi dotted name for what type/kind of output this is.
        '''
        return 'veredi.math.event.output'

    # -------------------------------------------------------------------------
    # Math System
    # -------------------------------------------------------------------------

    def finalize(self,
                 root:  MathTree,
                 total: MathValueType) -> None:
        '''
        Get this event ready for publishing. Replaces _output and _total with
        these values.
        '''
        self._output = root
        self._total = total

    # -------------------------------------------------------------------------
    # To String
    # -------------------------------------------------------------------------

    def __repr_name__(self):
        return "MathOutEvent"

    def __str__(self):
        return (f"{self._str_name()}: "
                f"total: {self.total}, "
                f"math: {self.output}, "
                f"context: {str(self._context)}")

    def __repr__(self):
        return (f"<{self._str_name(self.__repr_name__())}: "
                f"total: {self.total}, "
                f"math: {repr(self.output)}, "
                f"context: {repr(self._context)}"
                ">")
