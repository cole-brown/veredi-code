# coding: utf-8

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    Optional, Union, Any, NewType, Iterable, Dict)
from veredi.base.null import null_or_none
if TYPE_CHECKING:
    from veredi.base.context import VerediContext


import logging
import enum


from veredi.base.null       import NullNoneOr, null_or_none
from veredi.base.strings    import label
from veredi.base            import numbers


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

LogLvlConversion = NewType('LogLvlConversion', NullNoneOr[Union['Level', int]])
'''
These input types can be converted to a log.Level.
'''


LoggerInput = NewType('LoggerInput', NullNoneOr[logging.Logger])
'''
Optional logger can be: Null, None, or a Python logging.Logger.
'''


@enum.unique
class SuccessType(enum.Enum):
    '''
    Success/failure into easier/more consistent strings to see in logs.
    '''
    # ------------------------------
    # Values
    # ------------------------------

    IGNORE = None
    '''Becomes the empty string.'''

    # ---
    # Standard
    # ---
    BLANK = '    '

    FAILURE = 'FAIL'

    SUCCESS = 'OK'

    NEUTRAL = '----'

    # ---
    # Dry Run?
    # ---
    _DRY_BLANK   = '____'
    '''Use `BLANK` and `resolve()` to this, please.'''

    _DRY_NEUTRAL = '_--_'  # (*shrug*)
    '''Use `NEUTRAL` and `resolve()` to this, please.'''

    _DRY_FAILURE = '_F__'  # F(ail)
    '''Use `FAILURE` and `resolve()` to this, please.'''

    _DRY_SUCCESS = '__K_'  # (O)k
    '''Use `SUCCESS` and `resolve()` to this, please.'''

    # ------------------------------
    # Functions
    # ------------------------------

    @classmethod
    def success_or_failure(klass: 'SuccessType',
                           check_success: Optional[Any],
                           check_failure: Optional[Any]) -> 'SuccessType':
        '''
        Tries to translate `check_success` and `check_failure` into either
        SUCCESS or FAILURE.

        If no successes or no failures to check, pass in SuccessType.IGNORE.

        Numbers will be successful if greater than zero.
        Generally, uses `bool(check)`.
        '''
        # Check for success.
        successful = False
        if check_success == SuccessType.IGNORE:
            successful = klass.SUCCESS
        else:
            successful = klass._ok_or_fail(check_success)

        # Check for failure.
        failure = True
        if check_failure == SuccessType.IGNORE:
            failure = klass.SUCCESS
        else:
            failure = klass._ok_or_fail(check_failure, invert=True)

        # Return result, preferring a failure.
        if successful != SuccessType.SUCCESS:
            return successful
        return failure

    @classmethod
    def _ok_or_fail(klass: 'SuccessType',
                    check: Any,
                    invert: bool = False) -> 'SuccessType':
        '''
        Translates `check` into SUCCESS or FAILURE.

        If `invert` is Truthy, will figure out SUCCESS/FAILURE as normal and
        then invert the result. That is - will check for failure, instead of
        checking for success.
        '''
        # If a number, succes is greater than zero.
        if isinstance(check, numbers.NumberTypesTuple):
            check = (check > 0)

        # bool(check) works for:
        #   - bools
        #   - iterators (not empty == success)
        #   - strings? (not empty == success)
        if bool(check):
            return klass.SUCCESS

        return klass.FAILURE

    @classmethod
    def valid(klass: 'SuccessType',
              success: NullNoneOr['SuccessType']) -> bool:
        '''
        Returns true if `success` is a SuccessType value other than IGNORE.
        '''
        return (not null_or_none(success)
                and success is not klass.IGNORE)

    @classmethod
    def normalize(klass: 'SuccessType',
                  success: 'SuccessInput',
                  dry_run: bool) -> 'SuccessType':
        '''
        Convert from any SuccessInput type to a SuccessType enum value.
        '''
        # ---
        # First, convert to SuccessType.
        # ---
        value = success
        # No-op?
        if isinstance(success, SuccessType):
            pass
        # Bool Conversion?
        elif success is True:
            value = SuccessType.SUCCESS
        elif success is False:
            value = SuccessType.FAILURE

        # 'Optional' option chosen?
        elif success is None:
            value = SuccessType.IGNORE

        # Error option chosen?
        else:
            raise ValueError("SuccessType.normalize: Cannot convert unknown "
                             f"input type {type(success)} '{success}' "
                             "to SuccessType value.")

        # ---
        # Next, dry run? Or other such thing?
        # ---
        return value.resolve(dry_run)

    def resolve(self, dry_run: bool) -> 'SuccessType':
        '''
        Converts a standard value to Dry-Run if `is_dry_run`.
        '''
        if (self is SuccessType.IGNORE
                or not dry_run):
            return self

        # Expect the naming scheme to always hold true.
        return SuccessType['_DRY_' + self.name]

    def __format__(self, format_spec: str) -> str:
        '''
        Check for our None value, then have string formatted.
        '''
        # Center ourself on a 6 char wide string:
        #    1: '['
        #  2-5: self.value
        #    6: ']'
        # Or, if value is None, just make a 6 char wide string (no brackets).
        value = ('[{:^4s}]'.format(self.value)
                 if self.value is not None else
                 (' ' * 6))
        return value.__format__(format_spec)

    def __str__(self) -> str:
        '''
        Returns value string of enum formatted into e.g.:
          '[ OK ]'
          '[_F__]'
          '[    ]'
          '      '
        '''
        return '{:^6s}'.format(self)


SuccessInput = NewType('SuccessInput', Union[SuccessType, bool, None])
'''
The 'success' input param for Log Groups logging can be a:
  - SuccessType enum value
  - True/False
    - True  -> SuccessType.SUCCESS
    - False -> SuccessType.FAILURE
  - None
    - None -> Normal log format instead of _FMT_SUCCESS_HUMAN.
'''


# ------------------------------
# Log Levels
# ------------------------------

@enum.unique
class Level(enum.IntEnum):
    '''
    Log level enum. Values are python's logging module log level ints.
    '''

    NOTSET   = logging.NOTSET
    DEBUG    = logging.DEBUG
    INFO     = logging.INFO
    WARNING  = logging.WARNING
    ERROR    = logging.ERROR
    CRITICAL = logging.CRITICAL

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    @staticmethod
    def valid(lvl: Union['Level', int]) -> bool:
        for known in Level:
            if lvl == known:
                return True
        return False

    @staticmethod
    def to_logging(lvl: LogLvlConversion) -> int:
        if null_or_none(lvl):
            lvl = Level.NOTSET
        return int(lvl)

    @staticmethod
    def from_logging(lvl: LogLvlConversion) -> 'Level':
        if null_or_none(lvl):
            return Level.NOTSET
        return Level(lvl)

    def will_output_at(self,
                       minimum:       Union['Level', int, None],
                       notset_return: Optional[bool] = None) -> bool:
        '''
        Returns True if self is a 'high' level to be output at `minimum` level.

        This could be called "greater than or equal to", except verbosity
        values go down as verbosity levels go up...

        Raises ValueError if self or `minimum` are Level.NOTSET unless
        `notset_return` is set to True/False, in which case that value
        is returned instead.
        '''
        min_level = Level.to_logging(minimum)

        # None/NOTSET is a bit of a grey area, but... there's an optional
        # return to use so:
        if min_level == Level.NOTSET:
            if isinstance(notset_return, bool):
                return notset_return
            raise ValueError(f"Cannot determine if {self} will output "
                             f"for unset minimum: {min_level}")
        if self == Level.NOTSET:
            if isinstance(notset_return, bool):
                return notset_return
            raise ValueError(f"Cannot determine if unset {self} will output "
                             f"for minimum: {min_level}")

        # Verbose enough if we're equal or our level is a stricter log level
        # than the minimum. Example: CRITICAL is verbose enough to be printed
        # when the minimum is DEBUG.
        return ((self == min_level)
                or self.most_verbose(self, min_level) == minimum)

    @staticmethod
    def most_verbose(lvl_a: Union['Level', int, None],
                     lvl_b: Union['Level', int, None],
                     ignore_notset: bool = True) -> 'Level':
        '''
        Returns whichever of `a` or `b` is the most verbose logging level.

        Converts 'None' to Level.NOTSET.

        if `ignore_notset` is True, this will try to get the most verbose and
        return 'the other one' if one is logging level NOTSET. Otherwise, this
        will consider logging level NOTSET as the MOST verbose level.

        NOTSET actually means "use the parent's logging level", so take care.
        '''
        lvl_a = Level.to_logging(lvl_a)
        lvl_b = Level.to_logging(lvl_b)

        # If we're ignoring NOTSET, check for it and return 'the other one' if
        # found. If 'the other one' is also NOTSET, well... we tried.
        if ignore_notset:
            if lvl_a == Level.NOTSET.value:
                return Level.from_logging(lvl_b)
            if lvl_b == Level.NOTSET.value:
                return Level.from_logging(lvl_a)

        # The logging levels are:
        #   NOTSET:    0
        #   DEBUG:    10
        #   ...
        #   CRITICAL: 50
        # So for the most verbose, we want the minimum. NOTSET was addressed
        # above in the 'ignore_notset' check, so here we just assume NOTSET is
        # the most verbose.
        lvl = min(lvl_a, lvl_b)
        return lvl

    @staticmethod
    def least_verbose(lvl_a: Union['Level', int, None],
                      lvl_b: Union['Level', int, None],
                      ignore_notset: bool = True) -> 'Level':
        '''
        Returns whichever of `a` or `b` is the least verbose (aka 'highest' or
        'most important') logging level.

        Converts 'None' to Level.NOTSET.

        if `ignore_notset` is True, this will try to get the least verbose and
        return 'the other one' if one is logging level NOTSET. Otherwise, this
        will consider logging level NOTSET as the MOST verbose level.

        NOTSET actually means "use the parent's logging level", so take care.
        '''
        # Makes comparing and returing easier to just convert now.
        lvl_a = Level.from_logging(lvl_a)
        lvl_b = Level.from_logging(lvl_b)

        # Find the most verbose and return the other one.
        most = Level.most_verbose(lvl_a, lvl_b, ignore_notset=ignore_notset)
        if most == lvl_a:
            return lvl_b
        return lvl_a

    # -------------------------------------------------------------------------
    # Python Functions
    # -------------------------------------------------------------------------

    def __str__(self) -> str:
        '''
        Python 'to string' function.
        '''
        return self.__class__.__name__ + '.' + self.name

    def __repr__(self) -> str:
        '''
        Python 'to repr' function.
        '''
        return self.__class__.__name__ + '.' + self.name


DEFAULT_LEVEL = Level.INFO
'''Veredi's default logging level.'''


# ------------------------------
# Logging "Groups"
# ------------------------------

@enum.unique
class Group(enum.Enum):
    '''
    A logging group is for relating certain logs to a log.Level indirectly.

    E.g. log.Group.SECURITY can be set to Level.WARNING, or turned down to
    Level.DEBUG, and all log.Group.SECURITY logs will dynamically log out at
    the current level for the group.
    '''

    # ------------------------------
    # Values
    # ------------------------------

    START_UP = 'start-up'
    '''Logs related to start up of Veredi, the game, etc.'''

    SHUTDOWN = 'shutdown'
    '''Logs related to shutdown of Veredi, the game, etc.'''

    REGISTRATION = 'registration'
    '''Logs related to registration.'''

    SECURITY = 'security'
    '''veredi.security.* logs, and related logs.'''

    DATA_PROCESSING = 'data-processing'
    '''Logs related to loading, processing, and saving data.'''

    PARALLEL = 'parallel'
    '''Logs related to multiproc, threading, asyncio.'''

    # TODO: more groups

    # ------------------------------
    # Functions
    # ------------------------------

    def __str__(self) -> str:
        '''
        Returns value string of enum.
        '''
        return self.value


@enum.unique
class GroupResolve(enum.Enum):
    '''
    For logging using multiple groups.

    Should it log at highest log.Level indicated by groups? Log out to each
    group in turn? etc.
    '''

    # ------------------------------
    # Values
    # ------------------------------

    HIGHEST = enum.auto()
    '''
    Group Log resolves to be the Group and Level of the highest (e.g. CRITICAL
    is higher than DEBUG) log Level. If there is a tie, the first in the
    collection is used.
    '''

    EACH = enum.auto()
    '''
    Group Log resolves to be logged to each group provided in the collection in
    the collection's order.
    '''

    # ------------------------------
    # Helpers
    # ------------------------------

    def resolve(self,
                groups: Iterable[Group],
                levels: Dict[Group, Level]) -> Iterable[Group]:
        '''
        Resolves the input `groups` into an iterable of groups to use to log
        out to given our GroupResolve value.
        '''
        out_groups = []

        # Resolve to just highest level.
        if self is GroupResolve.HIGHEST:
            highest_group = None
            highest_level = None
            for group in groups:
                group_level = levels[group]
                highest_of = Level.least_verbose(group_level, highest_level)
                # Just set if this is first time.
                if not highest_group:
                    highest_group = group
                    highest_level = group_level

                # Else set if we have a more verbose group.
                elif (highest_of == group_level
                      and group_level != highest_level):
                    highest_group = group
                    highest_level = group_level

                # Else, ignore and continue.

            # And only provide the highest group found.
            out_groups.append(highest_group)

        # Resolve to all groups? Just give them their thing back.
        elif self is GroupResolve.EACH:
            out_groups = groups

        # Resolve to "a programmer must fix this".
        else:
            msg = f"Cannot resolve {self} - not implemented currently."
            error = TypeError(msg, self, groups)
            # Don't log.exception()... We're in the log module and used by it.
            raise error

        return out_groups


# ------------------------------
# Logger Names
# ------------------------------

@enum.unique
class LogName(enum.Enum):

    ROOT = label.normalize('veredi')
    '''
    The default/root veredi logger.
    '''

    MULTIPROC = label.normalize(ROOT, 'multiproc')
    '''
    multiproc's logger for setting up/tearing down sub-processes.
    '''

    # TODO [2020-09-12]: More logger names. Some formats?

    def _make(self, *name: str) -> str:
        '''
        Make **ANY** LogName from `*name` strings.

        Should use `rooted()` unless you're special.
        '''
        return label.normalize(*name)

    def rooted(self, *name: str) -> str:
        '''
        Make a LogName rooted from LogName enum called from.
        Examples:
          LogName.ROOT.rooted('jeff')
            -> 'veredi.jeff'
          LogName.MULTIPROC.rooted('server', 'jeff')
            -> 'veredi.multiproc.server.jeff'
        '''
        return label.normalize(str(self), *name)

    def __str__(self) -> str:
        '''
        Returns value string of enum.
        '''
        return self.value
