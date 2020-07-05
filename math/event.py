# coding: utf-8

'''
Events for Math, Maths, Mathing, Mathers, and Jeff.
'''


# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Union, NewType
import enum
from decimal import Decimal

from veredi.base.context           import VerediContext
from veredi.game.ecs.base.identity import MonotonicId
from veredi.game.ecs.event         import Event

from .parser import MathTree


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

MathResultType = NewType('MathResult', Union[int, float, Decimal])
MathResult = (int, float, Decimal)


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
                 total: MathResultType) -> None:
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
    pass


# -----------------------------------------------------------------------------
# Output to Users
# -----------------------------------------------------------------------------

class MathOutputEvent(MathResult):  # TODO: MathResult /and/ OutputEvent?
    '''
    This class is for directing a finalized math result towards the
    command/event output flow.

    Can use as-is or subclass if needed.
    '''
    pass
