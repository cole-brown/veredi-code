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

import enum
import pathlib

from veredi.logger import log

from veredi.base.exceptions import ContextError
from veredi.base.context import VerediContext, PersistentContext


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Config's Persistent Context
# -----------------------------------------------------------------------------

class ConfigContext(PersistentContext):
    '''
    PersistentContext with some Config-specific things in very specific places.
    '''

    NAME = 'configuration'
    KEY  = 'configuration'

    @enum.unique
    class Link(enum.Enum):
        CONFIG = enum.auto()
        '''The Configuration object.'''

        KEYCHAIN = enum.auto()
        '''
        Iterable of keys into something in the Configuration object that is
        important to the receiver of a context, probably.
        '''

        PATH = enum.auto()
        '''A pathlib.Path to somewhere.'''

    def __init__(self,
                 path:        pathlib.Path,
                 back_link:   'Configuration',
                 name:        Optional[str] = None,
                 key:         Optional[str] = None) -> None:
        name = name or self.NAME
        key = key or self.KEY
        super().__init__(name, key)

        # Make sure the path is a directory.
        path = path if path.is_dir() else path.parent
        self.add(self.Link.PATH,   path)
        self.add(self.Link.CONFIG, back_link)

    def finish_init(self,
                    repo_ctx:    PersistentContext,
                    codec_ctx:   PersistentContext) -> None:
        '''
        Repo and Codec have to be created, and probably want a ConfigContext.
        So init one of us, make them, then call this to finish the init of us.
        '''
        self.pull_to_sub(repo_ctx)
        self.pull_to_sub(codec_ctx)

    # -------------------------------------------------------------------------
    # Config-Specific Stuff
    # -------------------------------------------------------------------------

    @classmethod
    def path(klass: Type['ConfigContext'],
             context: VerediContext) -> Optional[pathlib.Path]:
        '''
        Checks for a PATH link in config's spot in this context.
        '''
        # Get context dict, then try to get the config sub-context, then we can
        # check for PATH link.
        config_ctx = context._get().get(klass.KEY, {})
        path = config_ctx.get(klass.Link.PATH, None)
        return path

    @classmethod
    def config(klass: Type['ConfigContext'],
               context: VerediContext) -> Optional['Configuration']:
        '''
        Checks for a CONFIG link in config's spot in this context.
        '''
        # Get context dict, then try to get the config sub-context, then we can
        # check for CONFIG link.
        config_ctx = context._get().get(klass.KEY, {})
        config = config_ctx.get(klass.Link.CONFIG, None)
        return config

    @classmethod
    def keychain(klass: Type['ConfigContext'],
                 context: VerediContext) -> Optional[Iterable[Any]]:
        '''
        Checks for a KEYCHAIN link in config's spot in this context.
        '''
        # Get context dict, then try to get the config sub-context, then we can
        # check for KEYCHAIN link.
        config_ctx = context._get().get(klass.KEY, {})
        keychain = config_ctx.get(klass.Link.KEYCHAIN, None)
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

    # -------------------------------------------------------------------------
    # Unit Testing
    # -------------------------------------------------------------------------
    def ut_inject(self,
                  path:     Optional[pathlib.Path]    = None,
                  config:   Optional['Configuration'] = None,
                  keychain: Optional[Iterable[Any]]   = None) -> None:
        '''
        Unit testing.

        Inject any of these that are not None into their spot in the context.
        '''
        config_data = self._get().get(self.KEY, {})
        if path is not None:
            config_data[self.Link.PATH] = path
        if config is not None:
            config_data[self.Link.CONFIG] = config
        if keychain is not None:
            config_data[self.Link.KEYCHAIN] = keychain

    # -------------------------------------------------------------------------
    # To String
    # -------------------------------------------------------------------------

    def __repr_name__(self):
        return 'CfgCtx'
