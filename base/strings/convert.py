# coding: utf-8

'''
Convert Dict[Any, Any]/List[Any] to Dict[str, str]/List[str] values.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (Optional, Union, Type, NewType, Any, Callable,
                    Dict, List, Tuple, Set, FrozenSet)

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

ListToStr = NewType('ListToStr', Union[List, Tuple, Set, FrozenSet])
ListToStrTuple = (list, tuple, set, frozenset)

ListOut = NewType('ListOut', List[Union[str, Dict, List]])
'''
`list_to_str()` outputs a list with values cast to strings, except
that ListToStr-types and DictToStr-types are recursed into.
'''

DictToStr = NewType('DictToStr', Dict[Any, Any])

DictOut = NewType('DictOut', Dict[str, Union[str, Dict, List]])
'''
`dict_to_str()` outputs a dictionary with keys cast to strings, and values cast
to strings (except that values of ListToStr/DictToStr are recursed into).
'''


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def predicate_v(check_value: Any,
                predicate:   Callable[[Any], bool] = None) -> bool:
    '''
    Check `predicate`, if exists use it to test `check_value`.

    Always returns True if no `predicate`.
    Otherwise returns predicate's return value.
    '''
    if not predicate:
        return True
    return predicate(check_value)


def predicate_kv(check_key:   Any,
                 check_value: Any,
                 predicate:   Callable[[Any], bool] = None) -> bool:
    '''
    Check `predicate`, if exists use it to test `check_key` & `check_value`.

    Always returns True if no `predicate`.
    Otherwise returns predicate's return value.
    '''
    if not predicate:
        return True
    return predicate(check_key, check_value)


# -----------------------------------------------------------------------------
# Any -> str / Dict[str, ...] / List[...]
# -----------------------------------------------------------------------------

def to_str(input: Any,
           predicates: Dict[Type, Callable[[Any], bool]] = None
           ) -> DictOut:
    '''
    `predicates` should be a dictionary of types to predicate functions.
       - Keys should be any of the dict key or list entry types expected.

    Returns either:
      - `str(input)`
      - return value of `list_to_str(input)`
      - return value `dict_to_str(input)`
    '''
    if not valid(input, predicates):
        return None

    value = None

    if isinstance(input, dict):
        value = dict_to_str(input, predicates=predicates)

    # Side-excursion/possible recursion because interable?
    elif isinstance(input, ListToStrTuple):
        value = list_to_str(input, predicates=predicates)

    # Dunno. Just string it.
    else:
        value = str(input)

    return value


def valid(check:      Any,
          predicates: Dict[Type, Callable[[Any], bool]]) -> bool:
    '''
    If `predicates` is None, returns True.
    Else, checks `predicates` for a key of type(check).
      - If none, returns True.
      - Else returns the predicate's result.
    '''
    if not predicates:
        return True

    predicate = predicates.get(type(check), None)
    if not predicate:
        return True

    return predicate(check)


# -----------------------------------------------------------------------------
# Dict[Any, Any] -> Dict[str, str/Dict[str, ...]/List[...]]
# -----------------------------------------------------------------------------

def dict_to_str(dictionary:      DictToStr,
                predicates: Dict[Type, Callable[[Any], bool]] = None
                ) -> DictOut:
    '''
    Creates a copy of `dictionary` with all keys and values translated into
    strings.
      - Leaves sub-dicts and list values as dicts/lists, translates their
        entries.

    NOTE: RECURSIVE! Don't use unless logging or some other thing that's ok to
    die/take a while in bad cases.

    If `predicates` is supplied, they should return True for desired items.
    '''
    strings = {}
    if not dictionary:
        return strings

    for key, value in dictionary.items():
        output = to_str(value, predicates=predicates)
        if output is None:
            continue
        strings[str(key)] = output

    return strings


# -----------------------------------------------------------------------------
# List[Any] -> List[str]
# -----------------------------------------------------------------------------

def list_to_str(input:           ListToStr,
                predicates: Callable[[Any], bool] = None
                ) -> ListOut:
    '''
    Creates a copy of `input` with all values translated into strings.

    NOTE: RECURSIVE! Don't use unless logging or some other thing that's ok to
    die/take a while in bad cases.

    If `predicates` is supplied, they should return True for desired items.
    '''
    strings = []
    for item in input:
        output = to_str(item, predicates=predicates)
        if output is None:
            continue
        strings.append(output)

    return strings
