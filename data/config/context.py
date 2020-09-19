# coding: utf-8

'''
Helper classes for managing contexts for events, error messages, etc.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    Optional, Any, Type, Iterable)
if TYPE_CHECKING:
    from .config import Configuration
    from veredi.parallel.multiproc import SubToProcComm

from veredi.base.null import Nullable, Null

import enum
import pathlib

from veredi.logger import log

from veredi.base.exceptions import ContextError
from veredi.base.context import VerediContext, EphemerealContext
from veredi.data import background


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Config's Transient Context
# -----------------------------------------------------------------------------

class ConfigContext(EphemerealContext):
    '''
    EphemerealContext used by Configuration to make regestered objects.
    '''

    NAME = 'configuration'
    KEY  = 'configuration'

    @enum.unique
    class Link(enum.Enum):
        KEYCHAIN = enum.auto()
        '''
        Iterable of keys into something in the Configuration object that is
        important to the receiver of a context, probably.
        '''

        PATH = enum.auto()
        '''A pathlib.Path to somewhere. Can look in background.data if none
        supplied.'''

        LOG_LEVEL = enum.auto()
        '''
        A log level for things to config their sub-loggers.
        Should just be used for main set-up (of primary logger) or
        set-up of sub-processes (like mediator server).
        '''

        SUB_PROC = enum.auto()
        '''
        A SubToProcComm object to hold on to for a sub-process.
        '''

    def __init__(self,
                 path:        pathlib.Path,
                 dotted:      str,
                 key:         Optional[str] = None) -> None:
        key = key or self.KEY
        super().__init__(dotted, key)

        # Make sure the path is a directory.
        if path:
            path = path if path.is_dir() else path.parent
            self.add(self.Link.PATH, path)

    # -------------------------------------------------------------------------
    # Config-Specific Stuff
    # -------------------------------------------------------------------------

    @classmethod
    def path(klass: Type['ConfigContext'],
             context: VerediContext) -> Nullable[pathlib.Path]:
        '''
        Checks for a PATH link in config's spot in this context.

        If none, returns PATH from background.data.
        '''
        # Get context dict, then try to get the config sub-context, then we can
        # check for PATH link.
        config_ctx = context._get().get(klass.KEY, {})
        path = config_ctx.get(klass.Link.PATH, Null())
        if not path:
            path = background.data.path()
        return path

    @classmethod
    def config(klass: Type['ConfigContext'],
               context: VerediContext) -> Optional['Configuration']:
        '''
        Helper to get config object from ConfigContext, even though it's
        actually in the background context. We just redirect.
        '''
        return background.config.config

    @classmethod
    def keychain(klass: Type['ConfigContext'],
                 context: VerediContext) -> Nullable[Iterable[Any]]:
        '''
        Checks for a KEYCHAIN link in config's spot in this context.
        '''
        # Get context dict, then try to get the config sub-context, then we can
        # check for KEYCHAIN link.
        config_ctx = context._get().get(klass.KEY, {})
        keychain = config_ctx.get(klass.Link.KEYCHAIN, Null())
        return keychain

    @classmethod
    def exception(klass:     Type['ConfigContext'],
                  context:   VerediContext,
                  source:    Optional[Exception],
                  msg:       Optional[str],
                  *args:     Any,
                  **kwargs:  Any) -> None:
        '''
        Calls log.exception() to raise a ConfigError with message built from
        msg, args, kwargs and with supplied context.

        Sets stack level one more than usual so that caller of this should be
        the stacktrace of the exception.
        '''
        # An extra stacklevel should get us back to whoever called us...
        raise log.exception(
            source,
            ContextError,
            msg, *args, **kwargs,
            context=context,
            stacklevel=3)

    @classmethod
    def set_log_level(klass:   Type['ConfigContext'],
                      context: VerediContext,
                      level:   Optional[log.Level]) -> Nullable[log.Level]:
        '''
        Sets log_level in `context`. Pops if `level` is None.
        '''
        context._sub_set(klass.KEY,
                         klass.Link.LOG_LEVEL,
                         level)

    @classmethod
    def log_level(klass: Type['ConfigContext'],
                  context: VerediContext) -> Nullable[log.Level]:
        '''
        Returns log_level in `context` or Null.
        '''
        return context._sub_get(klass.KEY,
                                klass.Link.LOG_LEVEL)

    @classmethod
    def set_subproc(klass:   Type['config'],
                    context: VerediContext,
                    value:   'SubToProcComm') -> None:
        '''
        Sets a SubToProcComm. Pops if `value` is None.
        '''
        context._sub_set(klass.KEY,
                         klass.Link.SUB_PROC,
                         value)

    @classmethod
    def subproc(klass:   Type['config'],
                context: VerediContext) -> Nullable['SubToProcComm']:
        '''
        Returns a SubToProcComm or Null.
        '''
        comms = context._sub_get(klass.KEY,
                                 klass.Link.SUB_PROC)
        return comms or Null()

    # -------------------------------------------------------------------------
    # Unit Testing
    # -------------------------------------------------------------------------
    def ut_inject(self,
                  path:     Optional[pathlib.Path]    = None,
                  keychain: Optional[Iterable[Any]]   = None) -> None:
        '''
        Unit testing.

        Inject any of these that are not None into their spot in the context.
        '''
        config_data = self._get().get(self.KEY, {})
        if path is not None:
            config_data[self.Link.PATH] = path
        if keychain is not None:
            config_data[self.Link.KEYCHAIN] = keychain

    # -------------------------------------------------------------------------
    # To String
    # -------------------------------------------------------------------------

    def __repr_name__(self):
        return 'CfgCtx'
