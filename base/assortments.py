# coding: utf-8

'''
Generic collection-type or pair-ish or (named) tuple-ish things.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Union, TypeVar, Generic


from veredi.logs import logs


# -----------------------------------------------------------------------------
# Current / Next
# -----------------------------------------------------------------------------

CurrNextT = TypeVar('CurrNextT')
'''Generic type for CurrentNext type hinting.'''


class CurrentNext(Generic[CurrNextT]):
    '''
    Holds a current and future value of something.
    '''

    def __init__(self, current, next) -> None:
        self._current:      CurrNextT = current
        self._next:         CurrNextT = next
        self._freeze_next:  bool      = False

    # ------------------------------
    # Properties
    # ------------------------------

    @property
    def current(self) -> CurrNextT:
        '''
        Returns current value.
        '''
        return self._current

    @current.setter
    def current(self, value: CurrNextT) -> None:
        '''
        Sets current value.
        '''
        self._current = value

    @property
    def next(self) -> CurrNextT:
        '''
        Returns next value.
        '''
        return self._next

    @next.setter
    def next(self, value: CurrNextT) -> None:
        '''
        Sets next value.
        '''
        if self._freeze_next:
            kwargs = log.incr_stack_level(None)
            log.info(f"Currently next is frozen at {self._next}; "
                     f"cannot set next value to {value}.",
                     **kwargs)
            return
        self._next = value

    # ------------------------------
    # Helpers
    # ------------------------------

    def freeze(self, freeze_next: Union[bool, CurrNextT]) -> None:
        '''
        Freeze or unfreeze `self._next`.

        If `freeze_next` is a `CurrNextT` type, sets `next` to `freeze_next`
        for convenient "freeze to this value". This does not change `current`.

        If `freeze_next` is True or a Truthy CurrNextT, disables `next` setter.
        If `freeze_next` is False or a Falsy CurrNextT, enables `next` setter.
        '''
        if isinstance(freeze_next, type(self.next)):
            self.next = freeze_next
        self._freeze_next = bool(freeze_next)

    def set_if_invalids(self,
                        invalid: CurrNextT,
                        set_to:  CurrNextT) -> None:
        '''
        Helper for initializing. Will set self.next to `set_to` if and only if
        both self.current and self.next are `invalid`.
        '''
        if (self.current == invalid
                and self.next == invalid):
            self.next = set_to

    def cycle(self, set_next_to: Optional[CurrNextT] = None) -> CurrNextT:
        '''
        Moves `self.next` value to `self.current`, (optionally) sets
        `self.next` to `set_next_to`, and then returns the new self.current
        value.

        If `set_next_to` is None, this leaves `next` at its current value (so
        `next` == `current` in that case).

        If `self._freeze_next` is True, this ignores `set_next_to` entirely and
        leaves `next` unchanged.
        '''
        self.current = self.next
        if set_next_to:
            # 'freeze' is taken care of by this setter property.
            self.next = set_next_to

        return self.current


# TODO [2020-10-03]: PreviousCurrentNext seems useful? Implement if needed.


# -----------------------------------------------------------------------------
# Delta / Next
# -----------------------------------------------------------------------------

DeltaNextT = TypeVar('DeltaNextT')
'''Generic type for DeltaNext type hinting.'''


class DeltaNext(Generic[DeltaNextT]):
    '''
    Holds a delta and future value of something.

    E.g. delta of 10 and next of '103' could be for a system that wants to tick
    some part of a tick only every tenth tick.
    '''

    def __init__(self, delta, next) -> None:
        self._delta: DeltaNextT = delta
        self._next:  DeltaNextT = next

    # ------------------------------
    # Properties
    # ------------------------------

    @property
    def delta(self) -> DeltaNextT:
        '''
        Returns delta value.
        '''
        return self._delta

    @delta.setter
    def delta(self, value: DeltaNextT) -> None:
        '''
        Sets delta value.
        '''
        self._delta = value

    @property
    def next(self) -> DeltaNextT:
        '''
        Returns next value.
        '''
        return self._next

    @next.setter
    def next(self, value: DeltaNextT) -> None:
        '''
        Sets next value.
        '''
        self._next = value

    # ------------------------------
    # Helpers
    # ------------------------------

    def cycle(self, current: DeltaNextT) -> DeltaNextT:
        '''
        Moves self.next value to `current` + self.delta.

        Returns self.next.
        '''
        self.next = current + self.delta
        return self.next
