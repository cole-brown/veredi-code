# coding: utf-8

'''
A class for loading a definitions record.

Record can have multiple documents, like 'metadata' and 'system.definition'.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (Any, Iterable, Mapping, Dict)
from collections import abc
import enum

from veredi.logger import log

from veredi.base import vstring
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

    # ---
    # abc.Container
    # ---
    def __contains__(self, desired: DDKey) -> bool:
        '''
        Delegates to our main DataDict.
        '''
        return desired in self._definitions()

    # ---
    # To String
    # ---
    def __str__(self) -> str:
        return f"{type(self).__name__}({self._documents})"

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._documents})"
