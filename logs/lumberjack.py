# coding: utf-8

'''
Logging utilities for Veredi.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    Optional, Union, Any, Type, MutableMapping, Iterable)
if TYPE_CHECKING:
    from veredi.base.context    import VerediContext


# ------------------------------
# Python Logging & Stuff
# ------------------------------
import logging
from contextlib import contextmanager


# ------------------------------
# Veredi Logging & Stuff
# ------------------------------
from veredi.base.strings import label
from .                   import log


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# I'm a Lumberjack and I'm ok...
# -----------------------------------------------------------------------------

class Lumberjack:
    '''
    A logging class for creating/handling a logger whose parent/ancestor must
    be the veredi.logger.log base logger.
    '''

    # -------------------------------------------------------------------------
    # Constants
    # -------------------------------------------------------------------------

    _MEGA_NAME_FMT = '{name}.!!!DEBUG!!!'
    _HYPER_NAME_FMT = '{name}.☢☢DEBUG☢☢'

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def _define_vars(self) -> None:
        '''
        Instance variable definitions, type hinting, doc strings, etc.
        '''
        self._name: str = None
        '''Dotted name of the logger.'''

        self._logger: log.PyLogType = None
        '''The logger we use for sending out log messages.'''

        self._mega: log.PyLogType = None
        '''
        The logger we use for sending out extra debug messages. Currently only
        the ultra-mega-debug ones.
        '''

        self._hyper: log.PyLogType = None
        '''
        The logger we use for sending out extra debug messages. Currently only
        the ultra-hyper-debug ones.
        '''

    def __init__(self,
                 name:                str,
                 initial_level:       log.Level             = log.Level.NOTSET,
                 require_veredi_name: bool                        = True,
                 # handler:             Optional[logging.Handler]   = None,
                 formatter:           Optional[logging.Formatter] = None
                 ) -> None:

        self._define_vars()

        # ------------------------------
        # Set/Verify Name
        # ------------------------------
        self._name = name
        if require_veredi_name and not label.is_veredi(self._name):
            err_msg = ("Name must be a veredi-derived name (must start with "
                       f"'veredi.'). Got: '{name}'. If this is not the "
                       "desired functionality, set `require_veredi_name` "
                       "to False.")
            err = ValueError(err_msg, name, initial_level,
                             # require_veredi_name, handler, formatter)
                             require_veredi_name, formatter)
            raise log.exception(err, err_msg)

        # ------------------------------
        # Set-Up
        # ------------------------------
        self._logger = log.init_logger(self._name,
                                       initial_level,
                                       # handler=handler,
                                       formatter=formatter)

    # -------------------------------------------------------------------------
    # Handlers
    # -------------------------------------------------------------------------

    def remove_handler(self, handler: logging.Handler) -> None:
        '''
        Remove the specified handler from our logger, if we have it.
        '''
        log.remove_handler(handler, self._logger, self._name)

    # -------------------------------------------------------------------------
    # Levels
    # -------------------------------------------------------------------------

    @property
    def level(self) -> log.Level:
        '''Returns current log level of logger, translated into Level enum.'''
        level = log.Level(self._logger.level)
        return level

    @level.setter
    def level(self, level: log.LogLvlConversion = log.Level.NOTSET) -> None:
        '''
        Change logger's log level. See log.py for log.Level values.
        '''
        if not log.Level.valid(level):
            self.error("Invalid log level {}. Ignoring.", level)
            return

        log.set_level(level, self._logger)

    def min_level(self,
                  level: log.LogLvlConversion = log.Level.NOTSET) -> None:
        '''
        Set logger's level to min of current or level (by most verbose).
        '''
        if not log.Level.valid(level):
            self.error("Invalid log level {}. Ignoring.", level)
            return

        log.set_level_min(level, self._logger)

    def will_output(self,
                    *args: Union[log.LogLvlConversion, log.Group]) -> bool:
        '''
        Returns true if any supplied `args` (Group or Level) is high enough to
        output a log.
        '''
        return log.will_output(*args,
                               veredi_logger=self._logger)

    # -------------------------------------------------------------------------
    # Logging-by-Functionality Functions
    # -------------------------------------------------------------------------

    def group(self,
              group:         'log.Group',
              dotted:        str,
              msg:           str,
              *args:         Any,
              context:       'VerediContext'  = None,
              log_minimum:   log.Level        = None,
              log_success:   log.SuccessInput = log.SuccessType.IGNORE,
              log_dry_run:   Optional[bool]   = False,
              **kwargs:      Any) -> None:
        '''
        Log at `group` log.Level, whatever it's set to right now.
        '''
        kwargs = self._stack(1, **kwargs)
        log.group(group, dotted, msg,
                  *args,
                  veredi_logger=self._logger,
                  context=context,
                  log_minimum=log_minimum,
                  log_success=log_success,
                  log_dry_run=log_dry_run,
                  **kwargs)

    def group_multi(
            self,
            groups:        Iterable['log.Group'],
            dotted:        label.DotStr,
            msg:           str,
            *args:         Any,
            group_resolve: Optional[log.GroupResolve] = None,
            context:       'VerediContext'            = None,
            log_minimum:   log.Level                  = None,
            log_success:   log.SuccessInput           = None,
            log_dry_run:   Optional[bool]             = False,
            **kwargs:      Any) -> None:
        '''
        Logs to one or more of the `groups`, depending on `group_resolve`.
        Uses the log level, etc of each group logged out as.
        '''
        kwargs = self._stack(1, **kwargs)
        log.group_multi(groups, dotted, msg,
                        *args,
                        veredi_logger=self._logger,
                        group_resolve=group_resolve,
                        context=context,
                        log_minimum=log_minimum,
                        log_success=log_success,
                        log_dry_run=log_dry_run,
                        **kwargs)

    def security(self,
                 dotted:   str,
                 msg:      str,
                 *args:    Any,
                 context:  Optional['VerediContext'] = None,
                 success:  Optional[log.SuccessType] = None,
                 **kwargs: Any) -> None:
        '''
        Log a security-related message via our logger.

        NOTE: This is not a "log at this level" function. Rather, it is a "log
        this security-related log" function. The logging level this uses can
        change at any time. This just allows all security logs to stay grouped
        at the same level easily (and keep them there if/when the level
        changes).
        '''
        kwargs = self._stack(1, **kwargs)
        log.security(dotted, msg,
                     *args,
                     veredi_logger=self._logger,
                     context=context,
                     success=success,
                     **kwargs)

    def start_up(self,
                 dotted:   str,
                 msg:      str,
                 *args:    Any,
                 context:  Optional['VerediContext'] = None,
                 success:  Optional[log.SuccessType] = None,
                 **kwargs: Any) -> None:
        '''
        Log a start-up-related message via our logger.

        NOTE: this is not a "log at this level" function. Rather, it is a "log
        this start-up-related log" function. The logging level this uses can
        change at any time. This just allows all start-up logs to stay grouped
        at the same level easily (and keep them there if/when the level
        changes).
        '''
        kwargs = self._stack(1, **kwargs)
        log.start_up(dotted, msg,
                     *args,
                     veredi_logger=self._logger,
                     context=context,
                     success=success,
                     **kwargs)

    def shutdown(self,
                 dotted:   str,
                 msg:      str,
                 *args:    Any,
                 context:  Optional['VerediContext'] = None,
                 success:  Optional[log.SuccessType] = None,
                 **kwargs: Any) -> None:
        '''
        Log a shutdown-related message via our logger.

        NOTE: this is not a "log at this level" function. Rather, it is a "log
        this start-up-related log" function. The logging level this uses can
        change at any time. This just allows all shutdown logs to stay grouped
        at the same level easily (and keep them there if/when the level
        changes).
        '''
        kwargs = self._stack(1, **kwargs)
        log.shutdown(dotted, msg,
                     *args,
                     veredi_logger=self._logger,
                     context=context,
                     success=success,
                     **kwargs)

    def data_processing(self,
                        dotted:   str,
                        msg:      str,
                        *args:    Any,
                        context:  Optional['VerediContext'] = None,
                        success:  Optional[log.SuccessType] = None,
                        **kwargs: Any) -> None:
        '''
        Log a data-processing-related message via our logger.

        NOTE: This is not a "log at this level" function. Rather, it is a "log
        this data-processing-related log" function. The logging level this uses
        can change at any time. This just allows all data-processing logs to
        stay grouped at the same level easily (and keep them there if/when the
        level changes).
        '''
        kwargs = self._stack(1, **kwargs)
        log.data_processing(dotted, msg,
                            *args,
                            veredi_logger=self._logger,
                            context=context,
                            success=success,
                            **kwargs)

    def registration(self,
                     dotted:   str,
                     msg:      str,
                     *args:    Any,
                     context:  Optional['VerediContext'] = None,
                     success:  Optional[log.SuccessType] = None,
                     **kwargs: Any) -> None:
        '''
        Log a registration-related message via our logger.

        NOTE: This is not a "log at this level" function. Rather, it is a "log
        this registration-related log" function. The logging level this uses
        can change at any time. This just allows all registration logs to stay
        grouped at the same level easily (and keep them there if/when the level
        changes).
        '''
        kwargs = self._stack(1, **kwargs)
        log.data_processing(dotted, msg,
                            *args,
                            veredi_logger=self._logger,
                            context=context,
                            success=success,
                            **kwargs)

    def parallel(self,
                 dotted:   str,
                 msg:      str,
                 *args:    Any,
                 context:  Optional['VerediContext'] = None,
                 success:  Optional[log.SuccessType] = None,
                 **kwargs: Any) -> None:
        '''
        Log a parallel-related (multiproc, threading, asyncio) message via our
        logger.

        NOTE: This is not a "log at this level" function. Rather, it is a "log
        this registration-related log" function. The logging level this uses
        can change at any time. This just allows all parallel logs to stay
        grouped at the same level easily (and keep them there if/when the level
        changes).
        '''
        kwargs = self._stack(1, **kwargs)
        log.parallel(dotted, msg,
                     *args,
                     veredi_logger=self._logger,
                     context=context,
                     success=success,
                     **kwargs)

    # -------------------------------------------------------------------------
    # Logging-by-Level Functions
    # -------------------------------------------------------------------------

    def _stack(self,
               amount: int,
               **kwargs: Any) -> MutableMapping[Any, Any]:
        '''
        Increment the stack level by one (or more) to account for passing
        through these logging wrapper functions.

        Returns `kwargs` input with increased stack level.
        '''
        # Increment stack level by whatever 'amount' is...
        log.incr_stack_level(kwargs, amount)
        return kwargs

    def ultra_mega_debug(self,
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
        # ------------------------------
        # Create on demand.
        # ------------------------------
        if not self._mega:
            debug_name = self._MEGA_NAME_FMT.format(name=self._name)
            self._mega = log.init_logger(debug_name, self.level)

        # ------------------------------
        # Adjust Stack Level.
        # ------------------------------
        kwargs = self._stack(1, **kwargs)

        # ------------------------------
        # Make the call.
        # ------------------------------
        log.ultra_mega_debug(msg,
                             *args,
                             veredi_logger=self._mega,
                             context=context,
                             **kwargs)

    def ultra_hyper_debug(self,
                          msg:      str,
                          *args:    Any,
                          title:    Optional[str]             = None,
                          add_type: Optional[bool]            = False,
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
        # ------------------------------
        # Create on demand.
        # ------------------------------
        if not self._hyper:
            debug_name = self._HYPER_NAME_FMT.format(name=self._name)
            self._hyper = log.init_logger(debug_name, self.level)

        # ------------------------------
        # Adjust Stack Level.
        # ------------------------------
        kwargs = self._stack(1, **kwargs)

        # ------------------------------
        # Make the call.
        # ------------------------------
        log.ultra_hyper_debug(msg,
                              *args,
                              title=title,
                              add_type=add_type,
                              veredi_logger=self._hyper,
                              context=context,
                              **kwargs)

    def debug(self,
              msg:      str,
              *args:    Any,
              context:  Optional['VerediContext'] = None,
              **kwargs: Any) -> None:
        '''
        Log a debug level message via our logger.
        '''
        kwargs = self._stack(1, **kwargs)
        log.debug(msg,
                  *args,
                  veredi_logger=self._logger,
                  context=context,
                  **kwargs)

    def info(self,
             msg:      str,
             *args:    Any,
             context:  Optional['VerediContext'] = None,
             **kwargs: Any) -> None:
        '''
        Log a info level message via our logger.
        '''
        kwargs = self._stack(1, **kwargs)
        log.info(msg,
                 *args,
                 veredi_logger=self._logger,
                 context=context,
                 **kwargs)

    def warning(self,
                msg:      str,
                *args:    Any,
                context:  Optional['VerediContext'] = None,
                **kwargs: Any) -> None:
        '''
        Log a warning level message via our logger.
        '''
        kwargs = self._stack(1, **kwargs)
        log.warning(msg,
                    *args,
                    veredi_logger=self._logger,
                    context=context,
                    **kwargs)

    def error(self,
              msg:      str,
              *args:    Any,
              context:  Optional['VerediContext'] = None,
              **kwargs: Any) -> None:
        '''
        Log a error level message via our logger.
        '''
        kwargs = self._stack(1, **kwargs)
        log.error(msg,
                  *args,
                  veredi_logger=self._logger,
                  context=context,
                  **kwargs)

    def critical(self,
                 msg:      str,
                 *args:    Any,
                 context:  Optional['VerediContext'] = None,
                 **kwargs: Any) -> None:
        '''
        Log a critical level message via our logger.
        '''
        kwargs = self._stack(1, **kwargs)
        log.critical(msg,
                     *args,
                     veredi_logger=self._logger,
                     context=context,
                     **kwargs)

    def exception(self,
                  error:     Union[Exception, Type[Exception]],
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
            lumberjack.exception(
                error,
                "Cannot frobnicate {} from {}. {} instead.",
                source, target, nonFrobMunger,
                context=self.context
            )
            # Reraise error if desired like this.
            raise
        '''
        kwargs = self._stack(1, **kwargs)
        return log.exception(error,
                             msg,
                             *args,
                             veredi_logger=self._logger,
                             context=context,
                             **kwargs)

    def at_level(self,
                 level: log.Level,
                 msg: str,
                 *args: Any,
                 context:  Optional['VerediContext'] = None,
                 **kwargs: Any) -> None:
        '''
        Log at a programatically-decided logging level. Calls the class
        function for the level.
        '''
        kwargs = self._stack(1, **kwargs)
        log_fn = None
        if level == log.Level.NOTSET:
            self.exception(ValueError("Cannot log at NOTSET level.",
                                      msg, args, kwargs),
                           msg,
                           args,
                           kwargs)
        elif level == log.Level.DEBUG:
            log_fn = self.debug
        elif level == log.Level.INFO:
            log_fn = self.info
        elif level == log.Level.WARNING:
            log_fn = self.warning
        elif level == log.Level.ERROR:
            log_fn = self.error
        elif level == log.Level.CRITICAL:
            log_fn = self.critical

        log_fn(msg,
               *args,
               context=context,
               **kwargs)

    # -------------------------------------------------------------------------
    # `with` Context Manager
    # -------------------------------------------------------------------------
    @contextmanager
    def logging_at(self,
                   enabled:  bool                 = True,
                   level:    log.LogLvlConversion = log.Level.DEBUG,
                   bookends: bool                 = False):
        '''
        A 'with' statement context manager for changing a lumberjack's logging
        level temporarily.
        '''
        # ------------------------------
        # Set level temporarily.
        # ------------------------------
        original = self.level
        self.level = level

        # ------------------------------
        # Do the 'with' statement things.
        # ------------------------------
        yield self

        # ------------------------------
        # Reset level back.
        # ------------------------------
        self.level = original
