# coding: utf-8

'''
Logging utilities for Veredi.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    Optional, Union, Any, NewType, Type, Callable,
                    Mapping, MutableMapping, Iterable, Dict, List)
if TYPE_CHECKING:
    from veredi.base.context    import VerediContext


import logging
import datetime
import math


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

FMT_DATETIME = '%Y-%m-%d %H:%M:%S.{msecs:03d}%z'  # Yeah, this is fun.

# Could use logging.Formatter and set like so:
# _FMT_DATETIME = '%Y-%m-%d %H:%M:%S'
# _FMT_MSEC = '%s.%03d'
#     ...
#     formatter = logging.Formatter(fmt=_FMT_LINE_HUMAN,
#                             datefmt=_FMT_DATETIME,
#                             style=_STYLE)
#     formatter.default_time_format = _FMT_DATETIME
#     formatter.default_msec_format = _FMT_MSEC
#     ...
# But that would miss out on being able to stuff our msecs inside of the
# datetime str like I want...


# -----------------------------------------------------------------------------
# Time Formatter
# -----------------------------------------------------------------------------

class BestTimeFmt(logging.Formatter):
    '''
    Same as the default formatter except it formats the date a bit better.

    ISO-8601 with sep=' ' and timespec='millisecond', basically.
      (aka basically datetime.isoformat(sep=' ', timespec='millisecond')
    '''

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    # None.

    # -------------------------------------------------------------------------
    # Formatting
    # -------------------------------------------------------------------------

    def formatTime(self,
                   record:   logging.LogRecord,
                   fmt_date: str = None) -> str:
        converted = datetime.datetime.fromtimestamp(record.created)
        if fmt_date:
            time_str = converted.strftime(fmt_date)
            string = time_str.format(msecs=math.floor(record.msecs))
        else:
            time_str = converted.strftime("%Y-%m-%d %H:%M:%S")
            string = "{:s}.{:03d}".format(time_str, math.floor(record.msecs))
        return string
