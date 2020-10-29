# coding: utf-8

'''
Dictionary helpers and special classes.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Any, Dict, Iterable, Iterator


import enum

from veredi.logger import log

# TODO [2020-10-28]: Some stuff is missing type hinting.

# TODO [2020-09-22]: Use typing something or other to allow these to take
# in & use type hinting. E.g. self.foo: DoubleIndexDict[[str, int], Jeff]


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Double-Index Dictionaries
# -----------------------------------------------------------------------------

# TODO: generics for type hinting
class DoubleIndexDict:
    '''
    Dictionary that indexes values via two different keys (in two different
    dictionaries).

    The internal dictionaries will be available as 'self.<dict_name_0/1>' as
    provided in the init. E.g.:
      value = 42
      x = DoubleIndexDict('jeff', 'geoff')
      x.set(1, 'one', value)
      print(x.jeff[1] == x.geoff['one'])  # 'True'
    '''

    class _DefaultValue(enum.Enum):
        INVALID = enum.auto()

    def __init__(self, dict_name_0: str, dict_name_1: str) -> None:
        # Create our two dictionaries.
        self._data0: Dict[Any, Any] = {}
        self._data1: Dict[Any, Any] = {}

        self._name0 = dict_name_0
        self._name1 = dict_name_1

        # Push name/dict into our __dict__ so they can be dot accessed.
        self.__dict__[dict_name_0] = self._data0
        self.__dict__[dict_name_1] = self._data1

    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------

    def _get_data0(self) -> Dict[Any, Any]:
        '''
        Getter for 'dict_name_0' property.
        '''
        return self._data0

    def _get_data1(self) -> Dict[Any, Any]:
        '''
        Getter for 'dict_name_1' property.
        '''
        return self._data1

    def items(self) -> Iterable[Any]:
        '''
        Returns items dictionary view of one of the internal dict.
        '''
        return self._data0.items()

    def keys(self) -> Iterable[Any]:
        '''
        Returns keys dictionary view of one of the internal dict.
        '''
        return self._data0.keys()

    def values(self) -> Iterable[Any]:
        '''
        Returns values dictionary view of one of the internal dict.
        '''
        return self._data0.values()

    def __iter__(self) -> Iterator:
        '''
        Returns an iterator over self._data0.
        '''
        return iter(self._data0)

    # -------------------------------------------------------------------------
    # Getters / Setters for Keeping in Sync
    # -------------------------------------------------------------------------

    def get(self,
            key: Any,
            default: Optional[Any] = _DefaultValue.INVALID
            ) -> Optional[Any]:
        '''
        Search both dictionaries for key, returning value from first one found.
        Raises KeyError if not found unless `default` is set.
        '''
        if key in self._data0:
            return self._data0[key]

        elif key in self._data1:
            return self._data1[key]

        if default is self._DefaultValue.INVALID:
            msg = f"Key '{key}' not found in either dictionary."
            raise log.exception(KeyError(msg, key),
                                None,
                                msg)
        return default

    def set(self,
            key0: Any,
            key1: Any,
            value: Any) -> None:
        '''
        Sets value in both dictionaries.
        NOTE: Use this to keep the dictionaries in sync!
        '''
        self._data0[key0] = value
        self._data1[key1] = value

    def del_by_keys(self,
                    key0: Any,
                    key1: Any) -> None:
        '''
        Keeps both dicts in sync.
        '''
        # Make sure to try to delete from both, but allow any KeyError to
        # bubble up.
        try:
            del self._data0[key0]
        finally:
            del self._data1[key1]

    def del_by_value(self,
                     del_value: Any) -> None:
        '''
        Keeps both dicts in sync.
        '''
        # ---
        # Delete from data0.
        # ---
        del_keys = set()
        for key0, value0 in self._data0.items():
            if value0 == del_value:
                del_keys.add(key0)
        for key in del_keys:
            del self._data0[key]

        # ---
        # Delete from data1 too.
        # ---
        del_keys.clear()
        for key1, value1 in self._data1.items():
            if value1 == del_value:
                del_keys.add(key1)
        for key in del_keys:
            del self._data1[key]

    # -------------------------------------------------------------------------
    # Pythonic Functions
    # -------------------------------------------------------------------------

    def __getitem__(self, key):
        '''
        collections.abc.MutableMapping 'subscriptable' support.
        '''
        return self.get(key)

    def __setitem__(self, key, newvalue):
        '''
        collections.abc.MutableMapping 'subscriptable' support.
        '''
        # Not sure if there's a way to do this... Don't have any smart ideas
        # currently, so disallow.
        raise NotImplementedError("Cannot have subscriptable setter for "
                                  f"{self.__class__.__name__}. Need two keys.")

    def __delitem__(self, key) -> None:
        '''
        Delete item from dictionaries while only knowing one key.
        '''
        item = self.get(key)
        if not item:
            msg = f"Key '{key}' not found in either dictionary."
            raise log.exception(KeyError(msg, key),
                                None,
                                msg)

        # ---
        # Delete based on item.
        # ---
        self.del_by_value(item)

    def __len__(self) -> int:
        return len(self._data0)

    def __str__(self) -> str:
        '''To String.'''
        return repr(self)

    def __repr__(self) -> str:
        '''To Representation String.'''
        from pprint import pformat
        import textwrap
        indent = '  '
        start = f"<class DoubleIndexDict('{self._name0}', '{self._name0}'): "
        data0_str = textwrap.indent(pformat(self._data0), indent * 2)
        data1_str = textwrap.indent(pformat(self._data1), indent * 2)
        end = ">"
        return (start + '\n'
                + indent + self._name0 + ':\n'
                + data0_str + '\n'
                + indent + self._name1 + ':\n'
                + data1_str + '\n'
                + end)


# -----------------------------------------------------------------------------
# Two-Way Dictionaries
# -----------------------------------------------------------------------------

# ------------------------------
# 1-1 Dictionary
# ------------------------------

# from: https://stackoverflow.com/a/7657712/425816
class BijectiveDict(dict):
    '''
    A bijective (/exactly/ 1-to-1) dictionary. Can only handle collections
    which have unique keys /and/ unique values. No 2 keys can have the same
    value.

    Note that:
      1) The inverse directory bd.inverse auto-updates itself when the standard
         dict bd is modified.
      2) We can only have one of each key.
      3) We can only have one of each value.
      4) A KeyError will be throw if trying to insert a key/value which has a
         duplicate of an existing value (of a different key).
    '''

    def __init__(self,
                 *args: Any,
                 **kwargs: Any) -> None:
        # Init standard dictionary.
        super().__init__(*args, **kwargs)
        # Init inverse dictionary.
        self.inverse = {}
        for key, value in self.items():
            # Error if this violates bijective-ness (1-to-1).
            if value in self.inverse:
                raise KeyError(f"Value '{value}' exists twice in keys; "
                               "cannot create bijective dictionary.")
            # Okay; set it.
            self.inverse[value] = key

    def __setitem__(self, key, value) -> None:
        # ---
        # Update inverse dictionary.
        # ---
        # Error if this violates bijective-ness (1-to-1).
        if (key not in self.keys()
                and value in self.inverse.keys()):
            raise KeyError(f"Value '{value}' already exists in keys "
                           "(paired with '{self.inverse[value]}'); "
                           f"cannot set '{key}'.")

        # Set inverse key/value.
        self.inverse[value] = key

        # ---
        # Update standard dictionary.
        # ---
        super().__setitem__(key, value)

    def __delitem__(self, key) -> None:
        # ---
        # Update inverse dictionary.
        # ---
        del self.inverse[self[key]]

        # ---
        # Update standard dictionary.
        # ---
        super().__delitem__(key)


# ------------------------------
# 1-many Dictionary
# ------------------------------

# from: https://stackoverflow.com/a/21894086/425816
class BidirectionalDict(dict):
    '''
    A bidirectional (1-to-many) dict. Can handle some keys having the same
    value. In that case the list returned by inverse will have all the values.

    Note that:
      1) The inverse directory bd.inverse auto-updates itself when the standard
         dict bd is modified.
      2) The inverse directory bd.inverse[value] is always a list of key such
         that bd[key] == value.
      3) Unlike the BijectiveDict class, here we can have 2 keys having same
         value. The bd.inverse dict is a dictionary of lists of keys.
    '''

    def __init__(self, *args, **kwargs) -> None:
        # Init standard dictionary.
        super().__init__(*args, **kwargs)
        # Init inverse dictionary.
        self.inverse = {}
        for key, value in self.items():
            self.inverse.setdefault(value, []).append(key)

    def __setitem__(self, key, value) -> None:
        # ---
        # Update inverse dictionary list.
        # ---
        # Key already exists, so this is a 'change value'. So remove old
        # key/value from inverse.
        if key in self:
            self.inverse[self[key]].remove(key)
        # Now add new key/value.
        self.inverse.setdefault(value, []).append(key)

        # ---
        # Update standard dictionary.
        # ---
        super().__setitem__(key, value)

    def __delitem__(self, key) -> None:
        # ---
        # Update inverse dictionary list.
        # ---
        # Remove key from inverse list.
        self.inverse.setdefault(self[key], []).remove(key)
        # Remove empty list from inverse?
        if self[key] in self.inverse and not self.inverse[self[key]]:
            del self.inverse[self[key]]

        # ---
        # Update standard dictionary.
        # ---
        super().__delitem__(key)
