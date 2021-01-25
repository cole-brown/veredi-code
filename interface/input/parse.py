# coding: utf-8

'''
For converting user input into Veredi's math/roll syntax trees.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Any, Dict

from veredi.logger          import log

from veredi.base            import label
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
        self._bg_data: Dict[Any, Any] = None

        # TODO: Why are Parcel and Mather using hasattr? Not the usual
        # for Veredi __init__() functions...
        if not hasattr(self, '_math') or not self._math:
            self._math = Mather(context)

        # TODO [2020-06-14]: Others.
        #  - chat
        #  - hashtag/macros?
        #  - More, I'm sure...

        self.get_background()

    def dotted(self) -> label.DotStr:
        '''
        Returns our Veredi Dotted Label.
        '''
        return 'veredi.interface.input.parse.mather'

    def get_background(self) -> Dict[Any, Any]:
        '''
        Returns `self._bg_data`.
        '''
        if not self._bg_data:
            self._bg_data = {
                'dotted': self.dotted(),
            }

        return self._bg_data

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
        self._bg_data: Dict[Any, Any] = None

        # TODO: Why are Parcel and Mather using hasattr? Not the usual
        # for Veredi __init__() functions...
        if hasattr(self, '_parser') and self._parser:
            return

        config = background.config.config(self.__class__.__name__,
                                          self.dotted(),
                                          context)

        self._parser: MathParser = config.create_from_config('server',
                                                             'input',
                                                             'parser',
                                                             'math')

        self.get_background()

    def dotted(self) -> label.DotStr:
        '''
        Returns our Veredi Dotted Label.
        '''
        return 'veredi.interface.input.parse.mather'

    def get_background(self) -> Dict[Any, Any]:
        '''
        Returns `self._bg_data`.
        '''
        if not self._bg_data:
            self._bg_data = {
                'dotted': self.dotted(),
            }

        return self._bg_data

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
