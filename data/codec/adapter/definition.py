# coding: utf-8

'''
A class for loading a definitions record.

Record can have multiple documents, like 'metadata' and 'system.definition'.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Any, Iterable, Mapping, Dict, List
from veredi.base.null import Null, Nullable

from collections import abc
import enum

from veredi.logger import log

from veredi.base import vstring
from veredi.base                    import dotted
from veredi.data.config.hierarchy import Hierarchy
from .dict import DataDict, DDKey


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

@enum.unique
class DocType(enum.Enum):
    INVALID = None
    METADATA = 'metadata'
    DEF_SYSTEM = 'system.definition'

    @classmethod
    def from_str(klass: 'DocType', string: str):
        string = vstring.normalize(string)
        if string == klass.METADATA.value:
            return klass.METADATA
        elif string == klass.DEF_SYSTEM.value:
            return klass.DEF_SYSTEM

        msg = f"'{string}' is not a DocType value."
        raise log.exception(ValueError(msg),
                            None,
                            msg)


# -----------------------------------------------------------------------------
# Mappings
# -----------------------------------------------------------------------------

class Definition(abc.MutableMapping):
    '''
    Collection of documents, of which the definition one is the 'main' one.

    The dictionary interface we follow is for interacting with this 'main'
    definitions doc.
    '''

    ALIAS = 'alias'

    # ------------------------------
    # Initialization
    # ------------------------------

    def __init__(self,
                 main_type: 'DocType',
                 record: Iterable[Mapping[DDKey, Any]] = []) -> None:
        self._documents: Dict[str, DataDict] = {}
        self._main:      'DocType'           = main_type

        for doc in record:
            if Hierarchy.VKEY_DOC_TYPE not in doc:
                msg = ("Required (auto-injected) key "
                       f"'{Hierarchy.VKEY_DOC_TYPE}' is not in document.")
                raise log.exception(KeyError(msg, doc),
                                    None,
                                    msg)

            doc_type = DocType.from_str(doc[Hierarchy.VKEY_DOC_TYPE])
            self._add_doc(doc_type, doc)

    def _add_doc(self,
                 doc_type: 'DocType',
                 doc: Mapping[DDKey, Any]) -> None:

        if (doc_type == DocType.METADATA
                or doc_type == DocType.DEF_SYSTEM):
            self._add_singleton(doc_type, doc)
        else:
            msg = (f"Don't know what to do with document type {doc_type} "
                   "to create definition...")
            raise log.exception(ValueError(msg, doc),
                                None,
                                msg)

    def _add_singleton(self,
                       doc_type: 'DocType',
                       doc: Mapping[DDKey, Any]) -> None:
        if doc_type in self._documents:
            msg = (f"Document type {doc_type} exists more than once in the "
                   "record, but we are only allowed one.")
            raise log.exception(ValueError(msg, doc),
                                None,
                                msg)

        self._documents[doc_type] = DataDict(doc)

    # ------------------------------
    # System's Set-Up
    # ------------------------------
    def configure(self, primary_key: str) -> None:
        '''
        Configure this definition for the system's use.

        `primary_key` should be whatever the system cares about most.
        E.g. 'skill' for SkillSystem.
        '''
        self._key_prime = primary_key

    # ------------------------------
    # Helpers
    # ------------------------------

    def _normalize(self, input: str) -> str:
        '''
        Normalizes a string. Returns non-strings unharmed.
        '''
        retval = input
        if isinstance(retval, str):
            retval = vstring.normalize(input)
        return retval

    def _definitions(self) -> DataDict:
        '''
        Returns our 'main' document - the definitions.
        '''
        return self._documents[self._main]

    def exists(self, check: str) -> bool:
        '''
        Checks for `input` in main document under `self._key_prime`.
        Also checks for `input` in main document under 'alias'.
        '''
        primary = (check in self[self._key_prime])

        # if alias key exists, also check there
        alias   = (self.ALIAS in self._skill_defs
                   and check in self[self.ALIAS])

        return primary or alias

    def append_default(self, names: List[str]) -> None:
        '''
        Appends default key to names list.
        '''
        names.append(self['default']['key'])

    def unalias(self, names: List[str]) -> List[str]:
        '''
        Converts any aliases into their canonical names.

        Returns list of canonical names.
        '''
        canon = []
        for name in names:
            unaliased = self.get(self.ALIAS, Null()).get(name, None)
            canon.append(unaliased if unaliased else name)

    def canonical(self, string: str) -> Nullable[str]:
        '''
        Takes `string` and tries to normalize it to canonical value.
        e.g.:
          'strength' -> 'strength.score'
          'Strength' -> 'strength.score'
          'str.mod' -> 'strength.modifier'
        '''
        names = dotted.split(string)

        # Is the first part even a thing?
        if not names or not names[0]:
            return Null()
        else:
            check = names[0]
            # Is the first part even our's?
            if not self.exists(check):
                return Null()
            # else, it's a valid skill name/alias.

        # TODO: could also check for final element being an expected leaf name?
        if len(names) < 2:
            self.append_default(names)

        # And we're finally ready to canonicalize the names and
        # return the string.
        canon = self.unalias(names)
        return dotted.join(*canon)

    # ------------------------------
    # abc.MutableMapping
    # ------------------------------

    def __getitem__(self, key: DDKey) -> Any:
        '''
        Delegates to our main DataDict.
        '''
        key = self._normalize(key)
        data = self._definitions()
        # Pawn off on our main DataDict.
        return data[key]

    def __delitem__(self, key: DDKey) -> Any:
        '''
        Delegates to our main DataDict.
        '''
        key = self._normalize(key)
        data = self._definitions()
        # Pawn off on our main DataDict.
        del data[key]

    def __setitem__(self, key: DDKey, value: Any) -> None:
        '''
        Delegates to our main DataDict.
        '''
        key = self._normalize(key)
        data = self._definitions()
        # Pawn off on our main DataDict.
        data[key] = value

    def __iter__(self) -> Iterable:
        '''
        Iterate over our main DataDict.
        '''
        return iter(self._definitions())

    def __len__(self) -> int:
        '''
        Length of our main DataDict.
        '''
        return len(self._definitions())

    # ------------------------------
    # abc.Container
    # ------------------------------

    def __contains__(self, desired: DDKey) -> bool:
        '''
        Delegates to our main DataDict.
        '''
        return desired in self._definitions()

    # ------------------------------
    # Non-'Main' Documents
    # ------------------------------

    def doc(self, doc_type: 'DocType') -> Nullable[Mapping]:
        '''
        Get a non-'main' document from the definition. E.g. 'alias' part of
        AbilitySystem's def file.
        '''
        return self._documents[doc_type] or Null()

    # ------------------------------
    # To String
    # ------------------------------

    def __str__(self) -> str:
        return f"{type(self).__name__}({self._documents})"

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._documents})"
