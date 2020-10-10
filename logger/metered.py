# coding: utf-8

'''
Log metering to reduce spammy logs.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    Optional, Union, Any, Type,
                    Generic, TypeVar, NewType,
                    Dict, Tuple, Iterable)
if TYPE_CHECKING:
    import logging
    from decimal                import Decimal
    from veredi.time.machine    import MachineTime
    from veredi.base.exceptions import VerediError
    from veredi.base.context    import VerediContext

from . import log


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

MeterT = TypeVar('MeterT')
'''Generic type for MeteredLog type hinting.'''

MeterAmount = NewType('MeterAmount', Union['Decimal', int,  float])


# -----------------------------------------------------------------------------
# LogMeter - a meter for a specific metered type (MeterT) of a MeteredLog
# -----------------------------------------------------------------------------

class LogMeter(Generic[MeterT]):
    '''
    A single meter for a single metering type.

    Tracks how recently it logged for its type; fingerprints, data of recent
    logs; etc.
    '''

    FINGERPRINT_TRUNCATE_LEN = 20
    FINGERPRINT_FMT = "{level} {msg} {args} {kwargs}"

    # ------------------------------
    # Initialization
    # ------------------------------

    def __init__(self,
                 machine_time:     'MachineTime',
                 meter_type:       MeterT,
                 meter_amount_sec: MeterAmount,
                 fingerprint:      bool,
                 print_length:     int = FINGERPRINT_TRUNCATE_LEN) -> None:

        self.time: 'MachineTime' = machine_time
        '''A time object for us to use for getting current time.'''

        self.type: MeterT = meter_type
        '''What we are responsible for metering. e.g. SystemTick.APOPTOSIS'''

        self.amount_ns: int = self.time.sec_to_ns(meter_amount_sec)
        '''How long (nanoseconds) to squelch repeated logs.'''

        self._fingerprint_messages: bool = fingerprint
        '''
        Whether or not we should take fingerprints of logs. If not, just meters
        based on time since last log of our type.
        '''

        self._fingerprint_length: int = print_length
        '''
        What length we should truncate log messages to for fingerprinting.
        '''

        self._log_prints: Dict[int, int] = {}
        '''
        Log message prints -> timestamp of last monotonic_ns that log message
        was allowed through.
        '''

    def config(self,
               meter_amount_sec:    MeterAmount,
               run_garbage_collect: bool = False) -> None:
        '''
        Update the meter with new metering time (`meter_amount_sec`), possibly
        other things eventually.

        Will run self.garbage_collect() if `run_garbage_collect` is set to
        True.
        '''
        self.amount_ns = meter_amount_sec

        if run_garbage_collect:
            self.garbage_collect()

    # ------------------------------
    # Message Fingerprint Getter/Setter
    # ------------------------------

    def _msg_stamp_get(self,
                       msg_stamp: int) -> int:
        '''
        Checks our log metering data for this message stamp.

        If it exists, return the timestamp we have for when it was last
        approved for logging.

        If it doesn't exist, return 0 as the timstamp.
        '''
        return self._log_prints.get(msg_stamp, 0)

    def _msg_stamp_set(self,
                       msg_stamp: int,
                       now: int) -> None:
        '''
        Add a message-stamp/timestamp to our log metering data. Overwrites the
        previously allowed timestamp if it exists.

        Timestamp should always 'now'.
        '''
        self._log_prints[msg_stamp] = now

    def fingerprint(self,
                    level:    log.LogLvlConversion,
                    msg:      str,
                    *args:    Any,
                    **kwargs: Any) -> int:
        '''
        Convert msg into a fingerprint, returns fingerprint.

        If self.fingerprint is False, this will hash entire `msg`, `level`, and
        all `args`/`kwargs` as the 'fingerprint'.
        '''
        final_hash = None

        # ------------------------------
        # self.fingerprint = True
        # ------------------------------
        if self._fingerprint_length > 0:
            # Truncate msg and only use that and level for final hash.
            msg = msg[:self._fingerprint_length]
            final_hash = hash(
                self.FINGERPRINT_FMT.format(
                    level=log.Level.to_logging(level),
                    msg=msg,
                    args='',
                    kwargs=''))

        # ------------------------------
        # self.fingerprint = False
        # ------------------------------
        else:
            # Use full msg, level, and all args/kwargs for final hash.
            final_hash = hash(
                self.FINGERPRINT_FMT.format(
                    level=log.Level.to_logging(level),
                    msg=msg,
                    args=str(args),
                    kwargs=str(kwargs)))

        return final_hash

    def timeprint(self,
                  msg_print: int) -> int:
        '''
        Returns a monotonic_ns timestamp for when this msg_print last appeared
        in our records.
        '''
        # ------------------------------
        # self.fingerprint = True or False
        # ------------------------------
        # Currently doesn't matter. We'll look for the msg_print in our logging
        # data based on the fingerprint we got.

        # Look for a pre-existing timestamp for this msg_print. If none, return
        # 0 as the "never logged that" value.
        timestamp = self._msg_stamp_get(msg_print)
        return timestamp

    def _valid_time_delta(self,
                          now:       int,
                          timestamp: int) -> bool:
        '''
        Returns true if `now` is far enough away from `timestamp` to approve of
        the log (based on self.amount_ns).
        '''
        delta = now - timestamp
        log_approved = delta > self.amount_ns
        return log_approved

    def log(self,
            type:         MeterT,
            level:        log.LogLvlConversion,
            msg:          str,
            *args:        Any,
            **kwargs:     Any) -> bool:
        '''
        Decides whether or not to log this thing. Does not log itself.

        Returns True if it approves.
        '''
        if self.type != type:
            return False

        # ---
        # Get fingers and times stamped.
        # ---
        msg_stamp = self.fingerprint(level, msg, args, kwargs)
        timestamp = self.timeprint(msg_stamp)

        # ---
        # Log message?
        # ---
        now = self.time.monotonic_ns
        if not self._valid_time_delta(now, timestamp):
            return False

        # Save info, then return approval.
        self._msg_stamp_set(msg_stamp, now)
        return True

    # ------------------------------
    # Garbage Collection
    # ------------------------------

    def garbage_collect(self) -> None:
        '''
        Run through our log infos and drop any that are old enough to not
        matter anymore.
        '''
        now = self.time.monotonic_ns
        for msg_stamp in list(self._log_prints.keys()):
            timestamp = self._log_prints[msg_stamp]

            # Remove the log info if it is old enough to not matter.
            if self._valid_time_delta(now, timestamp):
                del self._log_prints[msg_stamp]


# -----------------------------------------------------------------------------
# MeteredLog - Meters logs to reduce spam.
# -----------------------------------------------------------------------------

class MeteredLog(Generic[MeterT]):
    '''
    Keeps track of a type and a message fingerprint.

    If type and fingerprint match a "recent" log/error, ignore this log/error.
    '''

    def __init__(self,
                 logger_name:   Optional[str],
                 initial_level: log.LogLvlConversion,
                 machine_time:  'MachineTime',
                 *meters:       Tuple[MeterT, MeterAmount],
                 fingerprint:   bool = True) -> None:
        '''
        `logger_name` should be None, if you want the veredi default logger, or
        a veredi dotted string.

        `machine_time` should be a MachineTime instance that supports
        monotonic_ns property.

        `initial_level` will be ignored if `logger_name` is Falsy.
        It should be None, for "whatever/don't care".

        `meters` will be used to set up our metering data. You should provide
        metering info for all meter types you plan on using this for.
          - Optionally, you can call meter() after initialization to create
            your meters.

        `fingerprint`:
          ==True will consider only the message (no args/kwargs),
            truncated, and the logging level of the message when determining
            whether to squelch it or not.

          ==False will consider the full message, the logging level,
            the args, and the kwargs when determining whether to squelch it
            or not.
        '''

        self._log_name: str = logger_name
        '''
        Name we'll use for our logger. If None, we will use veredi.log's
        default logger.
        '''

        self._logger: 'logging.Logger' = log.get_logger(logger_name,
                                                        initial_level)
        '''
        The Python Logger we will use to log our metered logs to.
        '''

        self._time: 'MachineTime' = machine_time
        '''
        MachineTime object for LogMeter timings.
        '''

        self._meters: Dict[MeterT, LogMeter] = {}
        '''
        Our logging meters by MeterT log-metering type.
        '''

        self._fingerprint: bool = fingerprint
        '''
        Wether LogMeters will consider a sub-set, or all, of the log info when
        determining whether to allow a message to be logged.
        '''

        # ---
        # Init our meters if we have any passed in.
        # ---
        for type, amount in meters:
            self.meter(type, amount)

    def meter(self,
              meter_type: MeterT,
              meter_amount: MeterAmount) -> None:
        '''
        Add/update a LogMeter based on `meter_type`, `meter_amount`.
        '''
        # If an existing LogMeter, reconfigure it and be done.
        existing = self._meters.get(meter_type, None)
        if existing:
            existing.config(meter_amount)
            return

        # Else make a new one.
        self._meters[meter_type] = LogMeter(
            self._time,
            meter_type,
            meter_amount,
            self._fingerprint)

    # -------------------------------------------------------------------------
    # Logging Functions
    # -------------------------------------------------------------------------

    def _meter_msg(self,
                   meter_type: MeterT,
                   msg: str) -> str:
        '''
        Add fact that it's a metered log and the meter type to the log message.
        '''
        return f"MeteredLog({meter_type}): {msg}"

    def log(self,
            meter_type: MeterT,
            level:      log.Level,
            msg:        str,
            *args:      Any,
            **kwargs:   Any) -> bool:
        '''
        Log `msg`, `args`, `kwargs` at `level`, or get squelched, depending on
        the LogMeter for the `meter_type`.

        Logs a KeyError log.exception if the `meter_type` doesn't exist as one
        of our LogMeters (does not rethrow it). Then presumes it's not
        squelched and continues on to log it.

        Returns True if logged, False if squelched.
        '''
        allow_log = True
        try:
            meter = self._meters[meter_type]
            allow_log = meter.log(meter_type,
                                  level,
                                  msg,
                                  *args,
                                  **kwargs)
        except KeyError as key_error:
            # Catch key error and don't rethrow - let the actual except
            # take precedence.
            log.exception(key_error,
                          None,
                          "Could not find a meter for metering type {}.",
                          meter_type)

        # If our LogMeter says it's ok to log, do it. Otherwise just ignore it.
        if not allow_log:
            return False

        # Log to the correct function based on `level`.
        kwargs = kwargs or {}
        log.incr_stack_level(kwargs)
        log.at_level(level,
                     self._meter_msg(meter_type, msg),
                     *args,
                     **kwargs,
                     veredi_logger=self._logger)
        return True

    def exception(self,
                  meter_type: MeterT,
                  error:      Exception,
                  wrap_type:  Optional[Type['VerediError']],
                  msg:        str,
                  *args:      Any,
                  context:    Optional['VerediContext'] = None,
                  associate:  Optional[Union[Any, Iterable[Any]]] = None,
                  **kwargs:   Any) -> Tuple[bool, Exception]:
        '''
        Logs `error`, `msg`, `args`, `kwargs` at `level`, or get squelched,
        depending on the LogMeter for the `meter_type`.

        Uses log.exception(). `error` will optionally get wrapped up in a
        VerediError type if a `wrap_type` is supplied.

        Logs a KeyError log.exception if the `meter_type` doesn't exist as one
        of our LogMeters (does not rethrow it). Then presumes it's not
        squelched and continues on to log it.

        Returns: Tuple of (bool, error)
          - bool:  True if logged, False if squelched.
          - error: passed in error if bool is False, or log.exception() return.
        '''
        allow_log = True
        try:
            meter = self._meters[meter_type]
            allow_log = meter.log(meter_type,
                                  log.Level.ERROR,
                                  msg,
                                  *args,
                                  **kwargs)
        except KeyError as key_error:
            # Catch key error and don't rethrow - let the actual except
            # take precedence.
            log.exception(key_error,
                          None,
                          "Could not find a meter for metering type {}.",
                          meter_type)

        # If our LogMeter says it's ok to log, do it. Otherwise just ignore it.
        if not allow_log:
            return (False, error)

        # Log to the correct function based on `level`.
        kwargs = kwargs or {}
        log.incr_stack_level(kwargs)
        logger_error = log.exception(error,
                                     wrap_type,
                                     self._meter_msg(meter_type, msg),
                                     *args,
                                     **kwargs,
                                     context=context,
                                     associate=associate,
                                     veredi_logger=self._logger)
        return (True, logger_error)

    # -------------------------------------------------------------------------
    # Garbage Collection
    # -------------------------------------------------------------------------

    def garbage_collect(self) -> None:
        '''
        Run a gc on all our meters.

        Just drops all log metering data on logs that have become old enough to
        no longer matter for metering.
        '''
        for meter in self._meters.values():
            meter.garbage_collect()
