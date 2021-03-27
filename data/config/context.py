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

from veredi.base.null import Nullable, Null, null_or_none

import enum
import pathlib

from veredi.logs            import log

from veredi.base.exceptions import ContextError
from veredi.base.context    import VerediContext, EphemerealContext
from veredi.data            import background


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

    # -------------------------------------------------------------------------
    # Constants
    # -------------------------------------------------------------------------

    NAME = 'configuration'
    KEY  = 'configuration'

    @enum.unique
    class Link(enum.Enum):
        KEYCHAIN = enum.auto()
        '''
        Iterable of keys into something in the Configuration object that is
        important to the receiver of a context, probably.
        '''

        ID = enum.auto()
        '''
        Some sort of ID. Perhaps a record id/key for loading from a repository.
        '''

        PATH = enum.auto()
        '''
        A pathlib.Path to somewhere. Can look in background.data if none
        supplied.
        '''

        LOG_LEVEL = enum.auto()
        '''
        A log level for things to config their sub-loggers.
        Should just be used for main set-up (of primary logger) or
        set-up of sub-processes (like mediator server).
        '''

        LOG_SERVER = enum.auto()
        '''
        A log level for things to config their sub-loggers.
        Should just be used for main set-up (of primary logger) or
        set-up of sub-processes (like mediator server).
        '''

        SUB_PROC = enum.auto()
        '''
        A SubToProcComm object to hold on to for a sub-process.
        '''

        UNIT_TESTING = enum.auto()
        '''
        Optional field for unit testing.
        '''

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def __init__(self,
                 path:        pathlib.Path,
                 dotted:      str,
                 key:         Optional[str] = None,
                 id:          Optional[Any] = None) -> None:
        key = key or self.KEY
        super().__init__(dotted, key)

        # Add path to the context data if given.
        if id:
            self.add(self.Link.ID, id)

        # Make sure the path is a directory.
        if path:
            path = path if path.is_dir() else path.parent
            self.add(self.Link.PATH, path)

    # -------------------------------------------------------------------------
    # Config-Specific Stuff
    # -------------------------------------------------------------------------

    @classmethod
    def id(klass: Type['ConfigContext'],
           context: VerediContext) -> Nullable[Any]:
        '''
        Checks for an ID link in config's spot in this context.

        If none, returns Null().
        '''
        id = context.sub_get(klass.Link.ID)
        if not id:
            log.debug("No id in context! context.id: {}, ",
                      id,
                      context=context)
        return id

    @classmethod
    def path(klass: Type['ConfigContext'],
             context: VerediContext) -> Nullable[pathlib.Path]:
        '''
        Checks for a PATH link in config's spot in this context.

        If none, returns PATH from background.manager.data.
        '''
        path = context.sub_get(klass.Link.PATH)
        if null_or_none(path):
            log.debug("No path in context; using background's. "
                      "context.path: {}, ",
                      "bg.path: {}",
                      path,
                      background.manager.data.path,
                      context=context)
            path = background.manager.data.path
        return path

    # @classmethod
    # def config(klass: Type['ConfigContext'],
    #            context: VerediContext) -> Optional['Configuration']:
    #     '''
    #     Helper to get config object from ConfigContext, even though it's
    #     actually in the background context. We just redirect.
    #     '''
    #     config = background.config.config(self.__class__.__name__,
    #                                       self.dotted(),
    #                                       context)
    #     return background.config.config

    @classmethod
    def keychain(klass: Type['ConfigContext'],
                 context: VerediContext) -> Nullable[Iterable[Any]]:
        '''
        Checks for a KEYCHAIN link in config's spot in this context.
        '''
        keychain = context.sub_get(klass.Link.KEYCHAIN)
        return keychain

    @classmethod
    def set_log_level(klass:   Type['ConfigContext'],
                      context: VerediContext,
                      level:   log.LogLvlConversion
                      ) -> None:
        '''
        Sets log_level in `context`. Pops if `level` is None.
        '''
        context._sub_set(klass.KEY,
                         klass.Link.LOG_LEVEL,
                         level)

    @classmethod
    def log_level(klass: Type['ConfigContext'],
                  context: VerediContext) -> log.Level:
        '''
        Returns log_level in `context` or Null.
        '''
        return log.Level.to_logging(
            context._sub_get(
                klass.KEY,
                klass.Link.LOG_LEVEL))

    @classmethod
    def set_log_is_server(klass: Type['ConfigContext'],
                          context: VerediContext,
                          is_server: bool) -> None:
        '''
        Set is_server in `context`. Pops if `is_server` is None.
        '''
        context._sub_set(klass.KEY,
                         klass.Link.LOG_SERVER,
                         is_server)

    @classmethod
    def log_is_server(klass: Type['ConfigContext'],
                      context: VerediContext) -> bool:
        '''
        Returns True if the process is a log_server.
        '''
        # _sub_get() returns None if key not found, which is convenient for
        # converting to a bool.
        return bool(context._sub_get(klass.KEY,
                                     klass.Link.LOG_SERVER))

    @classmethod
    def set_subproc(klass:   Type['ConfigContext'],
                    context: VerediContext,
                    value:   'SubToProcComm') -> None:
        '''
        Sets a SubToProcComm. Pops if `value` is None.
        '''
        context._sub_set(klass.KEY,
                         klass.Link.SUB_PROC,
                         value)

    @classmethod
    def subproc(klass:   Type['ConfigContext'],
                context: VerediContext) -> Nullable['SubToProcComm']:
        '''
        Returns a SubToProcComm or Null.
        '''
        comms = context._sub_get(klass.KEY,
                                 klass.Link.SUB_PROC)
        return comms or Null()

    @classmethod
    def set_testing(klass:   Type['ConfigContext'],
                    context: VerediContext,
                    value:   'SubToProcComm') -> None:
        '''
        Sets the unit-testing link field. Pops if `value` is None.
        '''
        context._sub_set(klass.KEY,
                         klass.Link.UNIT_TESTING,
                         value)

    @classmethod
    def testing(klass:   Type['ConfigContext'],
                context: VerediContext) -> Nullable[bool]:
        '''
        Returns the unit-testing link field or Null.
        '''
        unit_testing = context._sub_get(klass.KEY,
                                        klass.Link.UNIT_TESTING)
        return unit_testing or Null()

    # -------------------------------------------------------------------------
    # Unit Testing
    # -------------------------------------------------------------------------

    def ut_inject(self,
                  path:     Optional[pathlib.Path]    = None,
                  keychain: Optional[Iterable[Any]]   = None,
                  ut_flag:  Optional[bool]            = None,
                  **kwargs: Any) -> None:
        '''
        Unit testing.

        Inject any of these that are not None into their spot in the context.
        '''
        config_data = self._get().get(self.KEY, {})
        if path is not None:
            config_data[self.Link.PATH] = path
        if keychain is not None:
            config_data[self.Link.KEYCHAIN] = keychain
        if ut_flag is not None:
            config_data[self.Link.UNIT_TESTING] = ut_flag

        for key in kwargs:
            config_data[key] = kwargs[key]

    # -------------------------------------------------------------------------
    # To String
    # -------------------------------------------------------------------------

    def __repr_name__(self):
        return 'CfgCtx'
