# coding: utf-8

'''
Configuration file reader/writer for Veredi games.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Any, MutableMapping


from veredi.logs                  import log

from veredi.base.strings          import label

from veredi.data                  import background
from veredi.data.config.config    import Configuration
from veredi.data.config.hierarchy import Document

from .                            import zpath
from .exceptions                  import UnitTestError


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

DEFAULT_RULES = 'veredi.rules.d20.pf2'
'''
label.DotStr for the default ruleset for testing.
'''


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def rules(test_type: zpath.TestType,
          rules:    Optional[label.LabelInput]) -> label.DotStr:
    '''
    Returns a DotStr for the rules desired for the `test_type` and `rules`
    inputs.
    '''
    # Pretty simple right now...
    if not rules:
        rules = DEFAULT_RULES
    return rules


def manual(test_type:   zpath.TestType,
           rules_label: Optional[label.LabelInput],
           game_id:     Optional[Any],
           config_data: MutableMapping[str, Any]) -> None:
    '''
    Creaty a Configuration manually (i.e. from the supplied params).

    `rules` should be a Label for the ruleset's dotted name, e.g.
    'veredi.rules.d20.pf2' (it will default to this if None provided).

    `game_id` should be the game's id, e.g. 'test-campaign' (it will default to
    zpath.config_id(test_type, None) if None provided).
    '''
    if not rules_label:
        rules_label = rules(test_type, rules_label)

    if not game_id:
        game_id = zpath.config_id(test_type, game_id)

    return NoFileConfig(rules_label,
                        game_id,
                        config_data)


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

    # -------------------------------------------------------------------------
    # Class Constants
    # -------------------------------------------------------------------------

    _DOTTED_NAME = 'veredi.zest.zonfig.no-file-config'

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def __init__(self,
                 rules:       label.LabelInput,
                 game_id:     Any,
                 config_data: MutableMapping[str, Any]) -> None:
        '''Don't call super().__init__()... we Just do it ourselves so as to
        avoid the normal config file.'''

        # ---
        # Set up variables.
        # ---
        self._rules = label.normalize(rules)
        self._id = game_id

        # Indicates that we're special...
        # TODO [2020-06-16]: Better way of saying we're special.
        self._path = False

        # Our storage of the config data itself.
        self._config = config_data or {}

        self._repo = None
        self._serdes = None

        self._metadata = {
            background.Name.DOTTED.key: self.dotted(),
            'path':                     self._path,
            'rules':                    self._rules,
            'id':                       self._id,
            background.Name.SERDES.key: None,
            background.Name.REPO.key:   None,
        }

        # ---
        # After var set-up!
        # ---
        try:
            # Setup our context, import repo & serdes's.
            # Also includes a handy back-link to this Configuration.
            background.config.init(self._path,
                                   self)

            self._set_background()

        except Exception as err:
            raise log.exception(
                UnitTestError,
                "Found an exception when creating NoFileConfig...") from err

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
