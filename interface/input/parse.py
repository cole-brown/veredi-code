# coding: utf-8

'''
For converting user input into Veredi's math/roll syntax trees.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional

from veredi.logger          import log

from veredi.data            import background
from veredi.base.context    import VerediContext

from veredi.math.parser     import MathParser, MathTree


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

    def __init__(self,
                 context: VerediContext) -> None:
        '''
        Configure ourselves by getting our specific parser and transformer from
        the configuratiion.
        '''
        if not hasattr(self, '_math') or not self._math:
            self._math = Mather(context)

        # TODO [2020-06-14]: Others.
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

    def __init__(self, context: VerediContext) -> None:
        '''
        Configure ourselves by getting our specific parser and transformer from
        the configuratiion.
        '''
        if hasattr(self, '_parser') and self._parser:
            return

        config = background.config.config
        if not config:
            raise background.config.exception(
                context,
                'Mather requires a configuration to configure itself.')

        self._parser: MathParser = config.make(None,
                                               'server',
                                               'input',
                                               'parser',
                                               'math')

    def parse(self, string: str, milieu: Optional[str] = None) -> MathTree:
        '''
        Parse input and transform into Veredi Math Tree.
        '''
        return self._parser.parse(string, milieu)


# -----------------------------------------------------------------------------
# Unit Testing
# -----------------------------------------------------------------------------

class UTMather(Mather):
    def __init__(self,
                 parser: MathParser,
                 context: VerediContext) -> None:
        self._parser = parser
        super().__init__(context)

class UTParcel(Parcel):
    def __init__(self,
                 parser: MathParser,
                 context: VerediContext) -> None:
        self._math = UTMather(parser, context)
        super().__init__(context)
