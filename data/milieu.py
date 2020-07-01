# coding: utf-8

'''
Milieu: noun
    mi-lieu
  plural milieus or milieux

Definition:
  - The physical or social setting in which something occurs or develops.
  - environment
  - Needed another context, but have used 'context' for events and setup, and
    have used 'background' for overall game context...

For returning a value (e.g. a result from looking up 'strength.modifier'),
and the thing looked up (in case environment/context/whatever (I mean 'milieu')
is needed later for resolving it further).
'''


# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Union, NamedTuple


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

# Python's typing module's version of:
#   namedtuple('ValueMilieu', ['value', 'dotted'])
# i.e. a namedtuple with type hinting. Yay.
class ValueMilieu(NamedTuple):
    '''
    For returning a value (e.g. a result from looking up 'strength.modifier'),
    and the thing looked up (in case environment/context/whatever is needed
    later for resolving it further).

    ...I would have called it 'context' but that's already in heavy use, so
    'milieu'.
        "The physical or social setting in which something occurs
        or develops."
    Close enough?

    For an example, looking for an ability result from 'str.mod':
        AbilitySystem._get_value(component,
                                 'str.mod')
          -> ValueMilieu('(${this.score} - 10) // 2',
                         'strength.modifier')

    That return is useful because later someone needs to know
    what 'this.score' is:
        AbilitySystem._get_value(component,
                                 ('this.score', 'strength.modifier'))
          -> ValueMilieu(20,
                         'strength.score')
    '''
    value:  Union[str, int]
    milieu: str
