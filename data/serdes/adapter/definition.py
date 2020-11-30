# coding: utf-8

'''
A class for loading a definitions record.

Record can have multiple documents, like 'metadata' and 'system.definition'.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Union, Any, Iterable, Mapping, Dict, List
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
        # Short cut out of here?
        if primary:
            return primary

        # If alias key exists, also check there.
        alias   = (self.ALIAS in self
                   and check in self[self.ALIAS])
        return alias

    def _append_default(self, names: List[str]) -> None:
        '''
        Appends default key to names list.
        '''
        names.append(self['default']['key'])

    def _canon_make(self,
                    names: List[Union[List[str], str]],
                    no_error_log: bool = False,
                    raise_error: bool = True) -> Nullable[str]:
        '''
        The actual canonicalize step for self.canonical().

        If `no_error_log`, skips logging an error if encountered.

        If `raise_error` is True, raises a KeyError if it falls off the data
        while trying to canonicalize.
          - This can be undesireable when e.g. creating commands from aliases.
            See AbilitySystem for how it deals with things so that its 'mod'
            alias doesn't get registered as an ability command.
        '''

        canon = []
        length = len(names)
        bookmark = self[self._key_prime]
        for i in range(length):
            name = names[i]
            resolved = False
            if isinstance(name, str):
                # Normal case, just look for aliases to replace.
                standard = self.get(self.ALIAS, Null()).get(name, None)
                if standard:
                    canon.append(standard)
                    bookmark = bookmark.get(standard, Null())
                    resolved = True
            elif isinstance(name, list):
                # Special case - look for 'this' to resolve. [[0], 1, 2]
                peek = names[i + 1] if (i < (length - 1)) else None
                standard_list = self._canon_this(canon, name, peek)
                for each in standard_list:
                    canon.append(each)
                    bookmark = bookmark.get(each, Null())
                resolved = True

            if not resolved:
                # It was fine all along as-is.
                standard = name
                canon.append(standard)
                bookmark = bookmark.get(standard, Null())

            # Did we get off track somehow?
            if not bookmark:
                if raise_error:
                    raise KeyError(("Canonicalizing and we fell off the "
                                    "definitions data? "
                                    f"input: {names}, current: {canon}"),
                                   names, canon)
                # Else just log the error and give 'em Null().
                # Well, maybe log.
                if not no_error_log:
                    log.error(
                        "Canonicalizing and we fell off the definitions data? "
                        "input: {}, current: {}",
                        names, canon)
                return Null()

        # We've canonicalized. Are we at a leaf, or do we need maybe a default
        # value thrown in?
        if not isinstance(bookmark, (str, int, float)):
            self._append_default(canon)

        return dotted.join(*canon)

    def _canon_this(self,
                    canon: List[str],
                    these: List[str],
                    next:  str) -> List[str]:
        '''
        If a 'this' was found, it was replaced with the milieu. So we'll have
        one of these kinds of lists to deal with:

        ['speed']  <- No 'this'.
        ['agility', 'ranks']  <- No 'this'.
        [['strength', 'modifier'], 'score']  <- Had a 'this'.

        But _canon_make() has been going through, and we only get what's been
        canonicalized, and a 'this' that got replaced with 'these'. We need to
        figure out what is canon now. So we get `next` to peek at the next
        thing in order to figure out a resolution.

        ['speed']  <- No 'this'.
        ['agility', 'ranks']  <- No 'this'.
        [['strength', 'modifier'], 'score']  <- Had a 'this'.

        ['speed']  <- No 'this'.
        ['agility', 'ranks']  <- No 'this'.
        [['strength', 'modifier']]  <- Had a 'this'; no next.

        Returns list of canonical names. Using our examples:
          ['speed']
            - No 'this'; we're not responsible for adding in default.
          ['agility', 'ranks']
            - No 'this'; was complete.
          ['strength', 'score']
            - Had a 'this'; figured out correct replacement value.
          [['strength', 'modifier']]
            - Had a 'this'; no next; fail on purpose.
        '''
        if not next:
            msg = ("Trying to 'un-this' in order to canonicalize a name, but "
                   "there is nothing up next to warrent a 'this' reference? "
                   f"canon-so-far: {canon}, 'this': {these}, next: {next}")
            error = ValueError(msg, canon, these, next)
            raise log.exception(error, None, msg)

        # Push canon input into canon output; walk down definitions tree while
        # we're at it.
        canon_this = []
        bookmark = self[self._key_prime]
        for name in canon:
            bookmark = bookmark[name]
            canon_this.append(name)

        # Check each piece of the 'this' pie to see if it fits or not with
        # what's up next.
        return_these = []  # We only want to return pieces of `these`.
        for name in these:
            if (name in bookmark
                    and next in bookmark[name]):
                canon_this.append(name)
                return_these.append(name)

        # Don't add next - that's the caller's job. We just needed to
        # do our job.
        return return_these

    def canonical(self,
                  string: str,
                  milieu: str,
                  no_error_log: bool = False,
                  raise_error: bool = True) -> Nullable[str]:
        '''
        Takes `string` and its `milieu`, and tries to normalize it to
        canonical value.

        e.g.:
          'strength' -> 'strength.score'
          'Strength' -> 'strength.score'
          'str.mod' -> 'strength.modifier'

        If `no_error_log`, skips logging an error if encountered.

        If `raise_error` is True, raises a KeyError if it falls off the data
        while trying to canonicalize.
          - This can be undesireable when e.g. creating commands from aliases.
            See AbilitySystem for how it deals with things so that its 'mod'
            alias doesn't get registered as an ability command.
        '''
        names, check_this = dotted.this(string, milieu)

        # Is the first part even a thing?
        if not names or not names[0]:
            return Null()

        check = names[0]
        if not isinstance(check, str):
            # dotted.this may have given us an embedded list for
            # a 'this' replacement.
            check = check[0]

        # Is the first part even our's?
        if not self.exists(check):
            return Null()
        # else, it's a valid name/alias.
        return self._canon_make(names,
                                no_error_log=no_error_log,
                                raise_error=raise_error)

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

    # ------------------------------
    # Other Magic Methods
    # ------------------------------

    def __bool__(self) -> bool:
        anything_exists = bool(self._documents)
        main_exists = False
        if anything_exists:
            main_exists = bool(self._definitions())

            if not main_exists:
                log.warning("{} has data of some sort, but no "
                            "main document data (nothing under "
                            "key '{}').",
                            str(self), str(self.main))

        return anything_exists and main_exists
