# coding: utf-8

'''
A class for loading a definitions record.

Record can have multiple documents, like 'metadata' and 'definition.system'.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import List
from veredi.base.null import Null, Nullable


from veredi                import log
from veredi.base.strings   import label

from .record               import Record
from ..serdes.adapter.dict import DataDict


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Mappings
# -----------------------------------------------------------------------------

class Definition(Record):
    '''
    Collection of documents, of which the definition one is the 'main' one.

    The dictionary interface we follow is for interacting with this 'main'
    definitions doc.
    '''

    ALIAS = 'alias'

    # -------------------------------------------------------------------------
    # System's Set-Up
    # -------------------------------------------------------------------------

    def configure(self, primary_key: str) -> None:
        '''
        Configure this definition for the system's use.

        `primary_key` should be whatever the system cares about most.
        E.g. 'skill' for SkillSystem.
        '''
        self._key_prime = primary_key

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _definitions(self) -> DataDict:
        '''
        Returns our 'main' document - the definitions.
        '''
        return self._documents[self._main]

    def exists(self,
               path:  label.LabelInput) -> bool:
        '''
        If `path` is a str:
          - Expects dotted string - converts to a list using
            `label.regularize()`.
        Else, uses list provided.

        Then checks for a value in the main document at the end of the
        (converted) `path`.

        Also checks for `check` in main document under 'alias' if that exists.
        '''
        # First, check under our primary key.
        if super().exists(label.regularize(self._key_prime, path)):
            return True

        # Second, try the alias key, if it exists.
        if self.ALIAS in self:
            alias_exists = super().exists(label.regularize(self.ALIAS, path))
            return alias_exists

    def _append_default(self, names: List[str]) -> None:
        '''
        Appends default key to names list.
        '''
        names.append(self['default']['key'])

    def _canon_make(self,
                    names:        label.LabelInput,
                    no_error_log: bool = False,
                    raise_error:  bool = True) -> Nullable[str]:
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
                standard = self.get(self.ALIAS).get(name, None)
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

        return label.normalize(*canon)

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
            raise log.exception(error, msg)

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
        names, check_this = label.this(string, milieu)

        # Is the first part even a thing?
        if not names or not names[0]:
            return Null()

        check = names[0]
        if not isinstance(check, str):
            # label.this may have given us an embedded list for
            # a 'this' replacement.
            check = check[0]

        # Is the first part even our's?
        if not self.exists(check):
            return Null()
        # else, it's a valid name/alias.
        return self._canon_make(names,
                                no_error_log=no_error_log,
                                raise_error=raise_error)
