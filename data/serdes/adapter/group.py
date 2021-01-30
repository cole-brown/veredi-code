# coding: utf-8

'''
Veredi's Adapter classes for interfacing specific serdes backends to
Veredi systems.

This module is for grouping of data in certain ways.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (Optional, Union, Any,
                    Mapping, Iterable, Dict, Set, Tuple)
from collections import abc
import re


from veredi.logger      import log
from veredi.base.string import text

from .meta              import MetaMarker, MetaType


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

_KG_HASH = 'KeyGroup'
_UD_HASH = 'UserDefined'


# -----------------------------------------------------------------------------
# Grouping
# -----------------------------------------------------------------------------

# ------------------------------
# Key Groups
# ------------------------------

class KeyGroup(abc.MutableMapping, abc.Hashable):
    '''
    A list of elements with something in common has been grouped up. E.g.:
      - Knowledge skills.

    Nomenclature attempted:
    For item 'Knowledge (Weird Stuff)':
      - "full"   name/key: 'Knowledge (Weird Stuff)'
      - "group"  name/key: 'Knowledge'
      - "member" name/key: 'Weird Stuff'
    '''

    RE_FLAGS = re.IGNORECASE
    '''
    Don't care about case in our data.
    '''

    RE_MEMBER_KEY_FMT = (
        r'^'
        r'(?P<group>{name})'
        r'.*?'
        r'(?P<member>\w[\w\d\s:\'"-]*\w)'
        r'.*?'
        r'$'
    )
    '''
    Matches:
      - start of string
      - group 'group':
        - name (i.e. our 'group name')
      - any number of anything, lazy
      - group 'member' (i.e. a specific member of our group):
        - something alphanumeric
        - any number of something printable-ish
        - something alphanumeric
      - who cares, lazy
      - end of string
    '''

    FULL_NAME_PAREN_FMT = '{name} ({member_name})'
    '''Full Names with member-name in parenthesis.
    E.g. "Knowledge (Weird Stuff)"'''
    FULL_NAME_COLON_FMT = '{name}: {member_name}'
    '''Full Names with member-name in parenthesis.
    E.g. "Profession: Weirdologist"'''

    def __init__(self,
                 name: Union['KeyGroupMarker', str],
                 values: Mapping[str, Any] = {},
                 re_claim: Union[re.Pattern, str, None] = None,
                 re_member_key: Union[re.Pattern, str, None] = None,
                 full_name_fmt: Optional[str] = None) -> None:
        '''
        `name` is for our name/key. E.g. for the "Knowledge (Weird Things),
        Knowledge(Etc)" group, that would be "Knowledge."

        NOTE: `re_claim` that are re.Patterns should kindly use (or bitwise or
        into their own flags) the KeyGroup.RE_FLAGS.
        If no `re_claim`, the claim will be:
            '^' + name + '.*$'

        NOTE: `re_member_key` that are re.Patterns should kindly use (or
        bitwise or into their own flags) the KeyGroup.RE_FLAGS.
        If no `re_member_key`, the pattern will be:
            KeyGroup.RE_MEMBER_KEY_FMT.format(name=name)

          SUB-NOTE: Member-key's match is in the second group! First group
          contains key's name! Use the regex grouping names!
        '''

        self._name: str = (name.name
                           if isinstance(name, KeyGroupMarker) else
                           name)
        '''
        Our name/key. E.g. for the "Knowledge (Weird Things), Knowledge(Etc)"
        group, that would be "Knowledge."
        '''

        self._user_defined: Optional[MetaMarker] = None
        '''
        Normal DataDicts won't have this; others (e.g. system definitions)
        could possibly.
        '''

        self._hash: Tuple[str, str] = (_KG_HASH, self._name)
        '''Our values we care about for hashing purposes - shouldn't change
        during lifetime of object.'''

        self._mapping: Dict[str, Any] = {}
        '''Our group of member-name/keys and their values.'''

        self._re_claim: re.Pattern = None
        '''Our re.Pattern for matching a group name & member name to us.'''

        self._re_member_key: re.Pattern = None
        '''Our re.Pattern for matching a group name & member name to us.'''

        self._name_fmt: str = full_name_fmt or self.FULL_NAME_PAREN_FMT

        self._init_regex(re_claim, re_member_key)

        # Want our regexes initialized before setting our _mapping based on
        # input values.
        self.update(values)

    def update(self, values: Any) -> None:
        '''
        abc.MutableMapping interface.

        We want to look at the values first in case we're weird.
        '''
        # I don't know what to do with non-dicts yet, so...
        remove = set()
        if isinstance(values, dict):
            remove = self._check_metas(values)

        for each in remove:
            values.pop(each, None)

        # And always let parent do... whatever it is they do here.
        super().update(values)

    def _check_metas(self, values: Any) -> Set[Any]:
        '''
        Checks for MetaMarkers in the new values, processes them if found.

        Returns a set of MetaMarkers to be removed from values before feeding
        into super().update().
        '''
        remove = set()
        for each in values:
            if not isinstance(each, MetaMarker):
                continue
            elif each.type == MetaType.USER_DEFINED:
                self._meta_user_defined(each)
                remove.add(each)
                continue

            # Else... dunno.
            msg = "Don't know how to process MetaMarker type: {}"
            msg = msg.format(each.type)
            raise log.exception(
                ValueError(msg, each),
                msg)

        return remove

    def _meta_user_defined(self, value: MetaMarker):
        '''
        Sets our _user_defined meta member or raises an error if we've already
        got one.
        '''
        if self._user_defined:
            msg = "Can only have one {} MetaMarker per group."
            msg = msg.format(value.type)
            raise log.exception(
                ValueError(msg, value),
                msg)
        self._user_defined = value

    def _init_regex(self,
                    re_claim:      Union[re.Pattern, str, None] = None,
                    re_member_key: Union[re.Pattern, str, None] = None
                    ) -> None:
        '''
        Sets self._claim to an re.Pattern based on input.
        '''
        # ---
        # re_claim
        # ---
        if isinstance(re_claim, str):
            self._re_claim = re.compile(re_claim,
                                        re.IGNORECASE)
        elif isinstance(re_claim, re.Pattern):
            self._re_claim = re_claim
        else:
            self._re_claim = re.compile('^' + self._name + r'.*$',
                                        re.IGNORECASE)

        # ---
        # re_member_key
        # ---
        if isinstance(re_member_key, str):
            self._re_member_key = re.compile(re_member_key,
                                             re.IGNORECASE)
        elif isinstance(re_member_key, re.Pattern):
            self._re_member_key = re_member_key
        else:
            match_str = self.RE_MEMBER_KEY_FMT.format(name=self._name)
            self._re_member_key = re.compile(match_str,
                                             re.IGNORECASE)

    # ---
    # Full-Name / Full-Key
    # ---
    def full_name(self, member_key: str) -> str:
        '''
        Turn a member-key into a full-key / full-name.
        E.g. 'weird stuff' -> 'knowledge (weird stuff)'
        '''
        return self._name_fmt.format(self._name, member_key)

    def split_key(self,
                  full_key: str,
                  allow_only_member_key: bool = False) -> Tuple[str, str]:
        '''
        Splits a full-key into a tuple of (group-key, member-key).
        '''
        if isinstance(full_key, (UserDefinedMarker,
                                 KeyGroupMarker,
                                 KeyGroup)):
            full_key = full_key.name

        retval = None
        result = self._re_member_key.match(full_key)
        if result:
            group = self.normalize(result.group('group'))
            member = self.normalize(result.group('member'))
            retval = (group, member)
        elif allow_only_member_key:
            # Couldn't match our full-name regex to get a member-key out...
            # assume that we were given a member-key instead?
            retval = (None, self.normalize(full_key))
        else:
            msg = f"Could not split '{full_key}' into (group, member) keys."
            raise log.exception(
                ValueError(msg, full_key, allow_only_member_key),
                msg)

        return retval

    # ---
    # Group Name / Key
    # ---
    def matches(self, key: str) -> bool:
        '''
        Returns true if this key matches us.
        E.g. if we are 'knowledge' and key is too, yes.
        '''
        return self.normalize(self._name) == self.normalize(key)

    # ---
    # Member Name / Key
    # ---
    def member_key(self,
                   full_name: Union[str, 'UserDefinedMarker'],
                   allow_only_member_key: bool) -> str:
        '''
        Get a member-key out of the `full_name`.
        E.g. for full_name == "Knowledge (Weird Stuff)":
          member-key: "Weird Stuff"
        '''
        if isinstance(full_name, (UserDefinedMarker,
                                  KeyGroupMarker,
                                  KeyGroup)):
            full_name = full_name.name

        retval = None
        try:
            _, member = self.split_key(full_name, allow_only_member_key)
            retval = member
        except ValueError:
            # Going to allow the full_name as the member_key in this case...
            retval = self.normalize(full_name)

        return retval

    def normalize(self, input: str) -> str:
        '''
        Normalizes a string. Mostly just for lowercasing when KeyGroup.RE_FLAGS
        contains re.IGNORECASE.
        '''
        retval = input
        if (self.RE_FLAGS & re.IGNORECASE) == re.IGNORECASE:
            retval = text.normalize(input)

        return retval

    def claims(self, full_name: str):
        '''
        Returns true if this KeyGroup will claim `full_name` as a
        groupie of itself.
        '''
        match = self._re_claim.match(full_name)
        return bool(match)

    # ---
    # abc.MutableMapping
    # ---
    def __getitem__(self, key: str) -> Any:
        # Gotta turn full-name key into our member-key, then check for it.
        member_key = self.member_key(key, True)
        return self._mapping[member_key]

    def __delitem__(self, key: str) -> Any:
        member_key = self.member_key(key, True)
        del self._mapping[member_key]

    def __setitem__(self, key: str, value: Any) -> None:
        member_key = self.member_key(key, True)
        self._mapping[member_key] = value

    def __iter__(self) -> Iterable:
        return iter(self._mapping)

    def __len__(self) -> int:
        return len(self._mapping)

    # ---
    # abc.Container
    # ---
    def __contains__(self, key: str) -> bool:
        '''
        Interface for:
           "Knowledge (Weird Stuff)" in some_key_group

        First make sure it's for our group, then return true if we have the
        member.

        NOTE: If we've been meta'd as MetaType.USER_DEFINED, we will return
        true for anything that matches our group. This MetaType should not be
        used except in e.g. template or system definitions.
        '''
        group, member = self.split_key(key, True)

        # Can't just check group since we're allowing member-key-only in so
        # many places that it only made sense here too...
        if group:
            # Correct group?
            if not self.claims(group):
                return False

        # Meta tag overriding our behavior?
        if self._user_defined:
            return True

        # Normal case: Look for the member in our items.
        return member in self._mapping

    # ---
    # abc.Hashable: Dict/Set Key Interface
    # ---
    def __hash__(self):
        # We'll hash out to our key's name plus
        return hash(self._hash)

    def __eq__(self, other):
        '''
        Define equality by hash in order to compare KeyGroupMarkers to
        KeyGroups and vice versa.
        '''
        return hash(self) == hash(other)

    # ---
    # To String
    # ---
    def __str__(self) -> str:
        return (f"{type(self).__name__}({self._name}, {self._mapping}, "
                f"{self._re_claim}, {self._re_member_key})")

    def __repr__(self) -> str:
        return (f"{type(self).__name__}({self._name}, {self._mapping}, "
                f"{self._re_claim}, {self._re_member_key})")


class KeyGroupMarker(abc.Hashable):
    '''
    Placeholder for folks who want to build their data like, say:
    {
      'shenanigans': {...},
      'knowledge': {
        'weird stuff': {...},
      },
    }

    They can parse/translate 'knowledge' into this diet class, and DataDict
    will finish up for them:
    {
      'shenanigans': {...},
      KeyGroupMarker('knowledge'): {
        'weird stuff': {...}
      }
    }

    Pass that into a DataDict and it will pull the marker-key and its value out
    and turn them into a KeyGroup proper.
    '''

    def __init__(self, key: str) -> None:
        self._name: str = key
        self._hash: Tuple[str, str] = (_KG_HASH, self._name)

    @property
    def name(self) -> str:
        return self._name

    # ---
    # Hashable / Dict/Set Key Interface
    # ---
    def __hash__(self):
        # We'll hash out to our key's name plus
        return hash(self._hash)

    def __eq__(self, other):
        '''
        Define equality by hash in order to compare KeyGroupMarkers to
        KeyGroups and vice versa.
        '''
        return hash(self) == hash(other)

    # ---
    # To String
    # ---
    def __str__(self) -> str:
        return (f"{type(self).__name__}({self._name})")

    def __repr__(self) -> str:
        return (f"<{type(self).__name__}({self._name})>")


# ------------------------------
# User Defined
# ------------------------------

# TODO [2020-06-26]: Not a 'group' thing? meta.py maybe?
class UserDefinedMarker(abc.Hashable):
    '''
    An element that usually has a rule/data-defined name should instead have
    one defined by user in this instance. E.g.:
      - Profession skills can have the specific profession defined by user.
    '''

    def __init__(self, key: str) -> None:
        self._name: str = key
        self._hash: Tuple[str, str] = (_UD_HASH, self._name)

    @property
    def name(self) -> str:
        return self._name

    # ---
    # Hashable / Dict/Set Key Interface
    # ---
    def __hash__(self):
        # We'll hash out to our key's name plus
        return hash(self._hash)

    def __eq__(self, other):
        '''
        Define equality by hash in order to compare UserDefinedMarker to
        UserDefined and vice versa.
        '''
        return hash(self) == hash(other)

    # ---
    # To String
    # ---
    def __str__(self) -> str:
        return (f"{type(self).__name__}({self._name})")

    def __repr__(self) -> str:
        return (f"<{type(self).__name__}({self._name})>")
