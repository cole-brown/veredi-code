# coding: utf-8

'''
Configuration file reader/writer for Veredi games.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Any, MutableMapping

from veredi.logger          import log
from veredi.base.exceptions import VerediError

from veredi.data.config.config import Configuration
from veredi.data.config.context import ConfigContext
from veredi.data.config.hierarchy import Document


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def manual(config_data: MutableMapping[str, Any]) -> None:
    '''
    Creaty a Configuration manually (i.e. from the supplied data).
    '''
    return NoFileConfig(config_data)


# -----------------------------------------------------------------------------
# Unit-Testing Config Class
# -----------------------------------------------------------------------------

class NoFileConfig(Configuration):
    '''
    Config data for how a game will run and what stuff it will use.

    NoFileConfig takes all data in as a map/dict, and holds on to that, instead
    of reading from a file or something.

    So currently only used for unit tests, though it could perhaps become the
    base class for configs for specific backends? FileConfig, DbConfig...
    '''

    def __init__(self,
                 config_data: MutableMapping[str, Any]) -> None:
        '''Don't call super().__init__()... we Just do it ourselves so as to
        avoid the normal config file.'''

        # Indicates to ConfigContext that we're special...
        # §-TODO-§ [2020-06-16]: Better way of saying we're special.
        self._path = False

        # Our storage of the config data itself.
        self._config = config_data or {}

        try:
            # Setup our context, import repo & codec's.
            # Also includes a handy back-link to this Configuration.
            self._context = ConfigContext(self._path,
                                          self)

            self._repo = None
            self._codec = None

            # No point since no repo/codec.
            # self._context.finish_init(None,
            #                           None)
        except Exception as e:
            raise log.exception(e,
                                VerediError,
                                "Found an exception when creating...") from e

        # No load/set-up. All that is in our config_data, hand-crafted by the
        # finest unit-test artisans.
        # self._load()
        # self._set_up()

    # -------------------------------------------------------------------------
    # Unit-Testing Helpers
    # -------------------------------------------------------------------------

    def ut_inject(self,
                  value:     Any,
                  doc_type:  Document,
                  *keychain: str) -> None:
        '''
        Set `value` into our config data for `doc_type` at location specified
        by the `keychain` keys iterable.
        '''
        # Get document type data first.
        doc_data = self._config.get(doc_type, None)
        data = doc_data
        if data is None:
            log.debug("No doc_type {} in our config data {}.",
                      doc_type, self._config)
            return None

        # Now hunt for/create the keychain they wanted...
        for key in keychain[:-1]:
            data = data.setdefault(key, {})

        # And set the key.
        data[keychain[-1]] = value
