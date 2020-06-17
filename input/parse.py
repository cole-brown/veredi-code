# coding: utf-8

'''
For converting user input into Veredi's math/roll syntax trees.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from veredi.logger                  import log
from veredi.data.config.context     import ConfigContext
from veredi.data.exceptions     import ConfigError

from veredi.math.parser             import MathParser, MathTree

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

class Parcel:
    '''
    A collection of parsers.
    '''

    def __init__(self, context: ConfigContext) -> None:
        '''
        Configure ourselves by getting our specific parser and transformer from
        the configuratiion.
        '''
        if not context:
            raise log.exception(
                None,
                ConfigError,
                'Parcel requires a context to create/configure its parsers.')

        self._math = Mather(context)
        # §-TODO-§ [2020-06-14]: Others.
        #  - chat
        #  - hashtag/macros?
        #  - More, I'm sure...

    @property
    def math(self) -> 'Mather':
        '''Returns our Mather instance (Math-Parser Interface).'''
        return self._math


class Mather:
    '''
    Delegate/Mediator that creates actual MathParser from config data, then
    allows calls to it.

    Parses input strings into Veredi Math Trees.
    '''

    def __init__(self, context: ConfigContext) -> None:
        '''
        Configure ourselves by getting our specific parser and transformer from
        the configuratiion.
        '''
        if not context:
            raise log.exception(
                None,
                ConfigError,
                'Mather requires a context to configure itself.')

        config = ConfigContext.config(context)
        if not config:
            raise log.exception(
                None,
                ConfigError,
                'Mather requires a configuration to configure itself.')

        self._parser: MathParser = config.make(None,
                                               'input',
                                               'parser',
                                               'math')

    def parse(self, string: str) -> MathTree:
        '''
        Parse input and transform into Veredi Math Tree.
        '''
        return self._parser.parse(string)
