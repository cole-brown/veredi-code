# coding: utf-8

'''
A class for loading a record of save game data.

A Record Class can have multiple documents, like 'metadata' and 'game.record'.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (Union, Any, Protocol, NewType,
                    Iterable, Mapping, Dict, Tuple)
from veredi.base.null import Null, Nullable, is_null


from collections import abc
import enum
import itertools


from veredi.logs                  import log

from veredi.base.strings          import label, text
from veredi.data.config.hierarchy import Hierarchy
from ..serdes.adapter.dict        import DataDict, DDKey


# -----------------------------------------------------------------------------
# Data Types
# -----------------------------------------------------------------------------

@enum.unique
class DataType(enum.Enum):
    '''
    For use when you want to differentiate between, e.g. a game's Saved data
    and its Definition data.
    '''

    SAVED = enum.auto()
    '''
    Saved Data: Expected to change as a game progresses.

    Example: How many hitpoints the boss had in the middle of the boss fight
    when the save was triggered.
    '''

    DEFINITION = enum.auto()
    '''
    Definition Data: Expected to remain constant as a game progresses.

    Example: What a system should do with a command input to get dice rolled
    and a number output.
    '''


# -----------------------------------------------------------------------------
# Document Types
# -----------------------------------------------------------------------------

class AnyDocType(Protocol):
    '''
    Type hinting for all the DocType enums.
    '''

    @property
    def type(self) -> str:
        '''
        All DocType enums should be enums and already have this...
        '''
        ...


class DocType:
    '''
    Record document type strings, so they don't have to exist in multiple
    places.

    A collection of enums and helper methods.
    '''

    # ------------------------------
    # Base Document Types
    # ------------------------------
    @enum.unique
    class general(enum.Enum):
        # ------------------------------
        # Values
        # ------------------------------
        INVALID = None
        metadata = 'metadata'

        @property
        def type(self) -> str:
            '''
            All DocType enums should implement this in order to be considered
            valid for AnyDocType.
            '''
            return self.value

    # ------------------------------
    # Definition Document Types
    # ------------------------------
    @enum.unique
    class definition(enum.Enum):
        '''
        These are for defining rules about a game that should just exist from
        the start of the game.
        '''
        system = 'definition.system'
        game   = 'definition.game'

        @property
        def type(self) -> str:
            '''
            All DocType enums should implement this in order to be considered
            valid for AnyDocType.
            '''
            return self.value

    # ------------------------------
    # Saved Document Types
    # ------------------------------
    @enum.unique
    class saved(enum.Enum):
        '''
        These are for records of saved data about the current state of the
        game, an entity, or whatever.
        '''
        game = 'saved.game'

        @property
        def type(self) -> str:
            '''
            All DocType enums should implement this in order to be considered
            valid for AnyDocType.
            '''
            return self.value

    # -------------------------------------------------------------------------
    # Methods
    # -------------------------------------------------------------------------

    @classmethod
    def types(klass: ['DocType']) -> Tuple[enum.Enum]:
        '''
        Returns all of DocType's enum types in a tuple.
        '''
        return (klass.general,
                klass.definition,
                klass.saved)

    @classmethod
    def verify_and_get(klass:    ['DocType'],
                       doc_type: Union[str, enum.Enum]) -> str:
        '''
        Normalizes string, verifies that it is one of our DocTypes, and returns
        the validated, normalized string.

        Raises a ValueError if verification fails.
        '''
        # Sanity check / convert input to string.
        string = doc_type
        if isinstance(string, enum.Enum):
            string = doc_type.type
        if not isinstance(string, str):
            msg = (f"'{doc_type}' is not valid. Must be a string or "
                   "string-backed Enum. "
                   f"Got: {type(doc_type)}, value: {string}")
            raise log.exception(ValueError(msg, doc_type), msg)

        # Expect whatever - normalize to lowercase.
        string = text.normalize(string)

        # Chain together all our enums so as to do a dumb search:
        for each_type in itertools.chain(klass.types()):
            for each in each_type:
                if string == each.type:
                    return each.type

        # Didn't find it anywhere. Error out.
        msg = f"'{string}' is not a DocType value."
        raise log.exception(ValueError(msg, string), msg)


AnyDocTypeInput = NewType('AnyDocTypeInput',
                          Union[str, AnyDocType])
'''
Since `DocType` is a class/namespace of enums of strings, the valid
DocTypes are: strings and DocType's actual enums (which must follow the
AnyDocType protocol).
'''


# -----------------------------------------------------------------------------
# Record Base Class
# -----------------------------------------------------------------------------

class Record(abc.MutableMapping):
    '''
    Collection of documents, of which the definition one is the 'primary' one.

    The dictionary interface we follow is for interacting with this 'primary'
    document.
    '''

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def _define_vars(self) -> None:
        '''
        Instance variable definitions, type hinting, doc strings, etc.
        '''

        self._documents: Dict[str, DataDict] = {}
        '''
        All our record's documents.
        '''

        self._primary_doc: str = None
        '''
        Name string of our main document. E.g. 'game.definition' for a game
        definition.
        '''

    def __init__(self,
                 primary_doc: 'AnyDocTypeInput',
                 documents: Iterable[Mapping[DDKey, Any]] = []) -> None:
        '''
        `primary_doc`: The record's primary DocType.
        `documents`:   The deserialized record data.
        '''
        self._define_vars()

        # Sanity check and set main name.
        self._primary_doc = DocType.verify_and_get(primary_doc)

        # Check and insert all the documents.
        for doc in documents:
            if Hierarchy.VKEY_DOC_TYPE not in doc:
                msg = ("Required (auto-injected) key "
                       f"'{Hierarchy.VKEY_DOC_TYPE}' is not in document.")
                raise log.exception(KeyError(msg, doc), msg)

            doc_type = doc[Hierarchy.VKEY_DOC_TYPE]
            self._add_document(doc_type, doc)

    def _add_document(self,
                      unverified_type: 'AnyDocTypeInput',
                      document:        Mapping[DDKey, Any]) -> None:
        '''
        Add `document` as `doc_type` to our documents.

        Calls `DocType.verify_and_get(doc_type)`, so exceptions from that can
        be raised.

        ValueError can also be raised if a document of `doc_type` already
        exists.
        '''
        doc_type = DocType.verify_and_get(unverified_type)

        if doc_type in self._documents:
            msg = (f"Document type {doc_type} exists more than once in the "
                   "record, but we are only allowed one.")
            raise log.exception(ValueError(msg, doc_type, document), msg)

        self._documents[doc_type] = DataDict(document)

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _normalize(self, input: Union[str, Any]) -> Union[str, Any]:
        '''
        Normalizes a string. Returns non-strings unharmed.
        '''
        retval = input
        if isinstance(retval, str):
            retval = text.normalize(input)
        return retval

    def _main(self) -> DataDict:
        '''
        Returns our 'main' document - the definitions.
        '''
        return self._documents[self._primary_doc]

    def get(self,
            *path: label.LabelInput) -> Nullable[Any]:
        '''
        Regularizes `path` to a dotted list:

        Returns value in main document under (converted) `path`.
          - Returns Null() if `path` does not exist.
        '''
        path = label.regularize(path)

        # Find out if there's anything at the end of the path.
        place = self._main()
        for key in path:
            # Check so we don't raise KeyError.
            if key not in place:
                return Null()

            # Update our place in the path and continue on to the next key.
            place = place[key]

        # We got here, so the path is either only a partial path, or we found a
        # leaf. We don't check for the difference right now, only return what
        # we ended up with.
        #
        # TODO: Figure out a way to return Null() if we're only a partial path?
        #   - Does DataDict have recursive DataDicts for sub-entries or
        #     something?
        return place

    def exists(self,
               path:  label.LabelInput) -> bool:
        '''
        If `path` is a str:
          - Expects dotted string - converts to a list using
            `label.regularize()`.
        Else, uses list provided.

        Then checks for a value in the main document at the end of the
        (converted) `path`.
        '''
        # Find if anything is at that path.
        value = self.get(path)

        # It either exists or we got Null.
        return not is_null(value)

    # -------------------------------------------------------------------------
    # abc.MutableMapping
    # -------------------------------------------------------------------------

    def __getitem__(self, key: DDKey) -> Any:
        '''
        Delegates to our main DataDict.
        '''
        key = self._normalize(key)
        data = self._main()
        # Pawn off on our main DataDict.
        return data[key]

    def __delitem__(self, key: DDKey) -> Any:
        '''
        Delegates to our main DataDict.
        '''
        key = self._normalize(key)
        data = self._main()
        # Pawn off on our main DataDict.
        del data[key]

    def __setitem__(self, key: DDKey, value: Any) -> None:
        '''
        Delegates to our main DataDict.
        '''
        key = self._normalize(key)
        data = self._main()
        # Pawn off on our main DataDict.
        data[key] = value

    def __iter__(self) -> Iterable:
        '''
        Iterate over our main DataDict.
        '''
        return iter(self._main())

    def __len__(self) -> int:
        '''
        Length of our main DataDict.
        '''
        return len(self._main())

    # -------------------------------------------------------------------------
    # abc.Container
    # -------------------------------------------------------------------------

    def __contains__(self, desired: DDKey) -> bool:
        '''
        Delegates to our main DataDict.
        '''
        return desired in self._main()

    # -------------------------------------------------------------------------
    # Non-'Main' Documents
    # -------------------------------------------------------------------------

    def document(self, doc_type: 'AnyDocTypeInput') -> Nullable[Mapping]:
        '''
        Get a non-'main' document from the definition. E.g. 'alias' part of
        AbilitySystem's def file.
        '''
        return self._documents[doc_type] or Null()

    # -------------------------------------------------------------------------
    # Python Functions
    # -------------------------------------------------------------------------

    def __str__(self) -> str:
        return f"{self.__class__.__name__}({self._documents})"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self._documents})"

    def __bool__(self) -> bool:
        '''
        Returns True /if and only if/:
          - We have any data.
          - That data has any data under the main key.

        In other words: Returns true if this record has its main data.
        '''
        anything_exists = bool(self._documents)
        main_exists = False
        if anything_exists:
            main_exists = bool(self._main())

            if not main_exists:
                log.warning("{} has data of some sort, but no "
                            "main document data (nothing under "
                            "key '{}').",
                            str(self), str(self._primary_doc))

        return anything_exists and main_exists
