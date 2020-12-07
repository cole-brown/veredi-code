# coding: utf-8

'''
Logging mixin class.

Gives a Lumberjack instance variable with a veredi dotted name to the class
it's mixed into.

Provides logging functions as class level functions for logging through the
lumberjack.
'''


# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    Optional, Any, MutableMapping)
if TYPE_CHECKING:
    from veredi.base.context    import VerediContext


# # ------------------------------
# # Python Logging & Stuff
# # ------------------------------
import logging as py_logging
# from contextlib import contextmanager


# ------------------------------
# Veredi Logging & Stuff
# ------------------------------
from veredi.base import label
from .           import log
from .lumberjack import Lumberjack


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# The Mixin
# -----------------------------------------------------------------------------

class LogMixin:
    '''
    A logging mixin class for creating/handling a logger whose parent/ancestor
    must be the veredi.logger.log base logger, and who has a dotted name of the
    main class it's mixed into.
    '''

    # -------------------------------------------------------------------------
    # Constants
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def _log_define_vars(self) -> None:
        '''
        Instance variable definitions, type hinting, doc strings, etc.
        '''

        self._lumberjack: Lumberjack = None
        '''The logger we use for sending out log messages.'''

    def __init__(self) -> None:
        '''
        Intentially no init. Save it all for _log_config().
        '''
        self._log_define_vars()

    def _log_config(self,
                    dotted:              str,
                    initial_level:       log.Level          = log.Level.NOTSET,
                    require_veredi_name: bool                           = True,
                    formatter:           Optional[py_logging.Formatter] = None
                    ) -> None:
        '''
        Configure / set-up / init / whatever the Lumberjack for LogMixin.
        '''

        # ------------------------------
        # Set-Up
        # ------------------------------
        self._lumberjack = Lumberjack(dotted,
                                      initial_level=initial_level,
                                      require_veredi_name=True,
                                      formatter=formatter)

    # -------------------------------------------------------------------------
    # Levels
    # -------------------------------------------------------------------------

    @property
    def _log_level(self) -> log.Level:
        '''
        Returns current log level of lumberjack.
        '''
        return self._lumberjack.level

    @_log_level.setter
    def _log_level(self,
                   level: log.LogLvlConversion = log.Level.NOTSET) -> None:
        '''
        Change lumberjack's log level. See log.py for log.Level values.
        '''
        self._lumberjack.level(level)

    def _log_will_output(self,
                         level: log.LogLvlConversion) -> bool:
        '''
        Returns true if supplied `level` is high enough to output a log.
        '''
        return self._lumberjack.will_output(level)

    def _log_stack(self,
                   amount: int = 1,
                   **kwargs: Any) -> MutableMapping[Any, Any]:
        '''
        Increment the stack level by one (or more) to account for passing
        through these logging wrapper functions.

        Returns `kwargs` input with increased stack level.
        '''
        # Increment stack level by whatever 'amount' is...
        kwargs = self._lumberjack._stack(amount, **kwargs)
        return kwargs

    # -------------------------------------------------------------------------
    # Logging-by-Functionality Functions
    # -------------------------------------------------------------------------

    def _log_group(self,
                   group:         'log.Group',
                   msg:           str,
                   *args:         Any,
                   **kwargs:      Any) -> None:
        '''
        Log at `group` log.Level, whatever it's set to right now.
        '''
        kwargs = self._log_stack(**kwargs)
        self._lumberjack.group(group, msg,
                               *args,
                               **kwargs)

    def _log_security(self,
                      msg:      str,
                      *args:    Any,
                      context:  Optional['VerediContext'] = None,
                      **kwargs: Any) -> None:
        '''
        Log a security-related message via our logger.

        NOTE: this is not a "log at this level" function. Rather, it is a "log
        this security-related log" function. The logging level this uses can
        change at any time. This just allows all security logs to stay grouped
        at the same level easily (and keep them there if/when the level
        changes).
        '''
        kwargs = self._log_stack(**kwargs)
        self._lumberjack.security(msg,
                                  *args,
                                  context=context,
                                  **kwargs)

    # -------------------------------------------------------------------------
    # Logging-by-Level Functions
    # -------------------------------------------------------------------------

    def _log_ultra_mega_debug(self,
                              msg:      str,
                              *args:    Any,
                              context:  Optional['VerediContext'] = None,
                              **kwargs: Any) -> None:
        '''
        Logs at Level.CRITICAL using logger named:
          self._name + '.!!!DEBUG!!!'

        All logs start with two newlines characters.

        All logs are prepended with a row starting with '!~DEBUG~!' and
        then repeating '~!'.
        All logs are prepended with a row of 'v'.

        All logs are appended with a row of '^'.
        All logs are appended with a row starting with '!~DEBUG~!' and
        then repeating '~!'.

        All logs end with two newlines characters.

        In other words, a log.ultra_mega_debug('test') is this:

          <log line prefix output>

          !~DEBUG~!~!~!~!~!~!~!~!~!....
          vvvvvvvvvvvvvvvvvvvvvvvvv....

          test

          ^^^^^^^^^^^^^^^^^^^^^^^^^....
          !~DEBUG~!~!~!~!~!~!~!~!~!....


        '''
        kwargs = self._log_stack(**kwargs)
        self._lumberjack.ultra_mega_debug(msg,
                                          *args,
                                          context=context,
                                          **kwargs)

    def _log_ultra_hyper_debug(self,
                               msg:      str,
                               *args:    Any,
                               context:  Optional['VerediContext'] = None,
                               **kwargs: Any) -> None:
        '''
        Logs at Level.CRITICAL using logger named:
          self._name + '.☢☢DEBUG☢☢'

        All logs start with two newlines characters.

        All logs end with two newlines characters.

        Basically, a lumberjack.ultra_hyper_debug('test') is this:

          <log line prefix output>

        ---
        -----
        --ultra-hyper-super-mega-debug-print
            test
        --ultra-hyper-super-mega-debug-print
        ---
        -----

        '''
        kwargs = self._log_stack(**kwargs)
        self._lumberjack.ultra_hyper_debug(msg,
                                           *args,
                                           context=context,
                                           **kwargs)

    def _log_debug(self,
                   msg:      str,
                   *args:    Any,
                   context:  Optional['VerediContext'] = None,
                   **kwargs: Any) -> None:
        '''
        Log a debug level message via our logger.
        '''
        kwargs = self._log_stack(**kwargs)
        self._lumberjack.debug(msg,
                               *args,
                               context=context,
                               **kwargs)

    def _log_info(self,
                  msg:      str,
                  *args:    Any,
                  context:  Optional['VerediContext'] = None,
                  **kwargs: Any) -> None:
        '''
        Log a info level message via our logger.
        '''
        kwargs = self._log_stack(**kwargs)
        self._lumberjack.info(msg,
                              *args,
                              context=context,
                              **kwargs)

    def _log_warning(self,
                     msg:      str,
                     *args:    Any,
                     context:  Optional['VerediContext'] = None,
                     **kwargs: Any) -> None:
        '''
        Log a warning level message via our logger.
        '''
        kwargs = self._log_stack(**kwargs)
        self._lumberjack.warning(msg,
                                 *args,
                                 context=context,
                                 **kwargs)

    def _log_error(self,
                   msg:      str,
                   *args:    Any,
                   context:  Optional['VerediContext'] = None,
                   **kwargs: Any) -> None:
        '''
        Log a error level message via our logger.
        '''
        kwargs = self._log_stack(**kwargs)
        self._lumberjack.error(msg,
                               *args,
                               context=context,
                               **kwargs)

    def _log_critical(self,
                      msg:      str,
                      *args:    Any,
                      context:  Optional['VerediContext'] = None,
                      **kwargs: Any) -> None:
        '''
        Log a critical level message via our logger.
        '''
        kwargs = self._log_stack(**kwargs)
        self._lumberjack.critical(msg,
                                  *args,
                                  context=context,
                                  **kwargs)

    def _log_exception(self,
                       error: Exception,
                       msg:       Optional[str],
                       *args:     Any,
                       context:   Optional['VerediContext'] = None,
                       **kwargs:  Any) -> None:
        '''
        Log the exception at ERROR level. See veredi.logger.log.exception for
        full details, but note we don't do any error type wrapping.

        Returns the error; not much use in this version where the error doesn't
        change types, so just do this, probably:
        except SomeError as error:
            # Reraise error if desired like this.
            raise self._log_exception(
                error,
                "Cannot frobnicate {} from {}. {} instead.",
                source, target, nonFrobMunger,
                context=self.context
            )
        '''
        kwargs = self._log_stack(**kwargs)
        self._lumberjack.exception(error,
                                   msg,
                                   *args,
                                   context=context,
                                   **kwargs)
        return error

    def _log_at_level(self,
                      level: log.Level,
                      msg: str,
                      *args: Any,
                      context:  Optional['VerediContext'] = None,
                      **kwargs: Any) -> None:
        '''
        Log at a programatically-decided logging level. Calls the class
        function for the level.
        '''
        kwargs = self._log_stack(**kwargs)
        self._lumberjack.at_level(level, msg,
                                  *args,
                                  context=context,
                                  **kwargs)
