# coding: utf-8

'''
Python Logger with extra levels.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

import logging


from .const import Level


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

class LoggerPlus(logging.Logger):
    '''
    Python logger with a few more logging functions for our extra log levels.
    '''

    def trace(self, msg, *args, **kwargs) -> None:
        '''
        Log 'msg % args' with severity 'Level.TRACE'.

        To pass exception information, use the keyword argument exc_info with
        a true value, e.g.

        logger.trace("Houston, we have a %s", "thorny problem", exc_info=1)
        '''
        if self.isEnabledFor(Level.TRACE.value):
            self._log(Level.TRACE.value, msg, args, **kwargs)

    def notice(self, msg, *args, **kwargs) -> None:
        '''
        Log 'msg % args' with severity 'Level.NOTICE'.

        To pass exception information, use the keyword argument exc_info with
        a true value, e.g.

        logger.notice("Houston, we have a %s", "thorny problem", exc_info=1)
        '''
        if self.isEnabledFor(Level.NOTICE.value):
            self._log(Level.NOTICE.value, msg, args, **kwargs)

    def alert(self, msg, *args, **kwargs) -> None:
        '''
        Log 'msg % args' with severity 'Level.ALERT'.

        To pass exception information, use the keyword argument exc_info with
        a true value, e.g.

        logger.alert("Houston, we have a %s", "thorny problem", exc_info=1)
        '''
        if self.isEnabledFor(Level.ALERT.value):
            self._log(Level.ALERT.value, msg, args, **kwargs)

    def emergency(self, msg, *args, **kwargs) -> None:
        '''
        Log 'msg % args' with severity 'Level.EMERGENCY'.

        To pass exception information, use the keyword argument exc_info with
        a true value, e.g.

        logger.emergency("Houston, we have a %s", "thorny problem", exc_info=1)
        '''
        if self.isEnabledFor(Level.EMERGENCY.value):
            self._log(Level.EMERGENCY.value, msg, args, **kwargs)

    def apocalypse(self, msg, *args, **kwargs) -> None:
        '''
        Log 'msg % args' with severity 'Level.APOCALYPSE'.

        To pass exception information, use the keyword argument exc_info with
        a true value, e.g.

        logger.apocalypse("Houston, we have a %s", "thorny problem", exc_info=1)
        '''
        if self.isEnabledFor(Level.APOCALYPSE.value):
            self._log(Level.APOCALYPSE.value, msg, args, **kwargs)
