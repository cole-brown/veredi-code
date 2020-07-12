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
from veredi.game.ecs.base.identity import MonotonicId
from veredi.game.ecs.event         import Event
from veredi.interface.output.event import OutputEvent, OutputType

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
                 id:           Union[int, MonotonicId],
                 type:         Union[int, enum.Enum],
                 context:      VerediContext,
                 root:         MathTree) -> None:
        self.set(id, type, context, root)

    def set(self,
            id:           Union[int, MonotonicId],
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

    def __init__(self,
                 source_id:   Union[int, MonotonicId],
                 source_type: Union[int, enum.Enum],
                 context:     VerediContext,
                 serial_id:   SerializableId,
                 output_type: OutputType,
                 root:        Optional[MathTree] = None) -> None:
        self.set(source_id, source_type, context,
                 serial_id, output_type,
                 root)

    def set(self,
            source_id:   Union[int, MonotonicId],
            source_type: Union[int, enum.Enum],
            context:     VerediContext,
            serial_id:   SerializableId,
            output_type: OutputType,
            root:        MathTree) -> None:
        super().set(source_id, source_type, context, serial_id, output_type)
        self.root = None
        self.total = None

    def reset(self) -> None:
        super().reset()
        self.root = None
        self.total = None

    # -------------------------------------------------------------------------
    # Output Things
    # -------------------------------------------------------------------------

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
        Get this event ready for publishing.
        '''
        self.root = root
        self.total = total

    # -------------------------------------------------------------------------
    # To String
    # -------------------------------------------------------------------------

    def __repr_name__(self):
        return "MathOutEvent"
