# coding: utf-8

'''
Registry for Encodables.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    Optional, Any, Type, Iterable, Dict, List)
from veredi.base.null import Null, null_to_none
if TYPE_CHECKING:
    from veredi.data.config.context import ConfigContext


from veredi.logs           import log
from veredi.data           import background
from veredi.base.strings   import pretty
from veredi.base.registrar import CallRegistrar, RegisterType
from veredi.base.strings   import label
from veredi.base           import numbers

from .const                import EncodedComplex, EncodedSimple, EncodedEither
from .encodable            import Encodable
from ..exceptions          import RegistryError


# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = [
    # ------------------------------
    # File-Local
    # ------------------------------

    # ---
    # Types
    # ---
    'EncodedComplex',
    'EncodedSimple',
    'EncodedEither',

    # ---
    # Classes
    # ---
    'EncodableRegistry',
]


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Encodables Registry
# -----------------------------------------------------------------------------

class EncodableRegistry(CallRegistrar):
    '''
    Registry for all the encodable types.
    '''

    # -------------------------------------------------------------------------
    # Dotted Name
    # -------------------------------------------------------------------------

    @classmethod
    def dotted(klass: 'EncodableRegistry') -> str:
        '''
        Returns this registrar's dotted name.
        '''
        return 'veredi.data.codec.encodable.registry'

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def _init_register(self,
                       encodable: Type[Encodable],
                       reg_args:  Iterable[str]) -> bool:
        '''
        This is called before anything happens in `register()`.

        Raise an error if a non-Encodable class tries to register.
        '''
        if not issubclass(encodable, Encodable):
            msg = ("EncodableRegistry only accepts Encodable subclasses for "
                   "registration. Got: {encodable}")
            error = ValueError(msg, encodable, reg_args)
            raise self._log_exception(error, msg)

        return True

    # -------------------------------------------------------------------------
    # Registration
    # -------------------------------------------------------------------------

    def _register(self,
                  encodable:  Type[Encodable],
                  reg_label:    Iterable[str],
                  # final key in `reg_args`
                  leaf_key:   str,
                  # A sub-tree of our registration dict, at the correct node
                  # for registering this encodable.
                  reg_ours:   Dict,
                  # A sub-tree of the background registration dict, at the
                  # correct node for registering this encodable.
                  reg_bg:     Dict) -> None:
        '''
        We want to register to the background with:
          { leaf_key: Encodable.type_field() }

        `reg_args` is the Iterable of args passed into `register()`.
        `reg_ours` is the place in our registry we placed this registration.
        `reg_bg` is the place in the background we placed this registration.
        '''
        # Get it's type field name.
        try:
            name = encodable.type_field()
        except NotImplementedError as error:
            msg = (f"{self.__class__.__name__}._register: '{type(encodable)}' "
                   f"(\"{label.regularize(*reg_label)}\") needs to "
                   "implement type_field() function.")
            self._log_exception(error, msg)
            # Let error through. Just want more info.
            raise

        # Set as registered cls/func.
        reg_ours[leaf_key] = encodable

        # Save to the background as a thing that has been registered at this
        # level.
        bg_list = reg_bg.setdefault('.', [])
        bg_list.append({leaf_key: name})

    # -------------------------------------------------------------------------
    # Decoding
    # -------------------------------------------------------------------------

    def simple(self,
               data:      Optional[EncodedSimple],
               data_type: Optional[Type[Encodable]] = None,
               ) -> Optional[Type[Encodable]]:
        '''
        Looks through registered encodables for one that supports
        Encoding.SIMPLE and claims the data.
        '''
        # None decodes to None.
        if data is None:
            return None

        self._log_debug(f"EncodableRegistry.simple: data: {type(data)}, "
                        f"data_type: {data_type}")

        registree = None

        # ---
        # Search for registered Encodable.
        # ---
        registree = self._search(self._registry,
                                 None,
                                 data,
                                 data_type=data_type)

        # ---
        # Found something or nothing... return it.
        # ---
        return registree

    def get(self,
            data:          Optional[EncodedEither],
            dotted:        Optional[str]             = None,
            data_type:     Optional[Type[Encodable]] = None,
            error_squelch: bool                      = False,
            fallback:      Optional[Type[Encodable]] = None,
            ) -> Optional[Type[Encodable]]:
        '''
        Get the registered Encodable that this `data` can maybe be decoded to,
        if any of our registered classes match `dotted` field in data, or
        claim() the `data`.

        If `data` is None, returns None.

        If `dotted` is supplied, try to get that Encodable from our registry.
        Use it or raise RegistryError if not found.

        If `data_type` is supplied, will restrict search for registered
        Encodable to just that class or its subclasses.

        `error_squelch` will only raise the exception, instead of raising it
        through log.exception().

        If nothing registered fits `data`:
          - If the `fallback` keyword arg is supplied, return that.
          - Else raise a ValueError.
        '''
        # None decodes to None.
        if data is None:
            return None

        self._log_debug(f"EncodableRegistry.get: data: {type(data)}, "
                        f"dotted: {dotted}, data_type: {data_type}")

        registree = None

        # ---
        # Too simple?
        # ---
        if isinstance(data, (str, *numbers.NumberTypesTuple)):
            self._log_debug("EncodableRegistry.get: Shouldn't be asking the "
                            "registry for registered class for simple data types. "
                            f"data: {type(data)}, "
                            f"dotted: {dotted}, data_type: {data_type}")
            return None

        # ---
        # Use dotted name?
        # ---
        if dotted:
            registree = self.get_by_dotted(dotted, None)

        # ---
        # Search for registered Encodable.
        # ---
        else:
            registry = self._registry
            data_dotted = label.from_map(data, error_squelch=True)
            if data_dotted:
                registree = self._search(registry,
                                         data_dotted,
                                         data,
                                         data_type=data_type)

        # ---
        # Did we find the correct registree?
        # ---
        if registree:
            # Find by claim?
            claiming, _, _ = registree.claim(data)
            if claiming:
                return registree
            else:
                self._log_debug(f"EncodableRegistry.get: Found registree for data, "
                                "but registree will not claim it. "
                                f"registree: {registree}, data: {type(data)}, "
                                f"dotted: {dotted}, data_type: {data_type}")

        # ---
        # Not Found: Fallback if provided?
        # ---
        if fallback:
            return fallback

        # ---
        # No Fallback: Error out.
        # ---
        msg = (f"{self.__class__.__name__}: "
               "No registered Encodable found for "
               f"data. data_dotted: {data_dotted}")
        extra = (", \n"
                 "registry:\n"
                 "{}\n\n"
                 "data:\n"
                 "{}\n\n")
        error = ValueError(msg, data, registree)
        if error_squelch:
            raise error
        raise self._log_exception(error, msg + extra,
                                  pretty.indented(registry),
                                  pretty.indented(data))

    def _search(self,
                place:     Dict[str, Any],
                dotted:    Optional[label.DotStr],
                data:      EncodedEither,
                data_type: Type[Encodable]) -> Optional[Encodable]:
        '''
        Provide `self._registry` as starting point of search.

        Searches the registry.

        If 'data_type' is supplied, will restrict search for registered
        Encodable to use to just that or subclasses.

        If `dotted` is provided, walks that keypath and
        returns whatever is registered to that.

        Otherwise, recursively walk our registry dict to find something that
        will claim() `data`.

        Returns registree or None.
        '''
        # Set data_type to any Encodable if not supplied.
        if data_type is None:
            data_type = Encodable

        # ---
        # Provided with a dotted key. Use that for explicit search.
        # ---
        # More like 'get' than search...
        if dotted and label.is_dotstr(dotted):
            keys = label.regularize(dotted)
            # Path shouldn't be long. Just let Null-pattern pretend to be a
            # dict if we hit a 'Does Not Exist'.
            for key in keys:
                place = place.get(key, Null())
            # Done, return either the registree or None.
            place = null_to_none(place)
            # Place must be:
            #   - An Encodable.
            #   - The same class or a subclass of data_type.
            if (not place
                    or (type(place) != data_type
                        and not issubclass(place, data_type))):
                # Don't return some random halfway point in the registry tree.
                place = None
            return place

        # ---
        # Search for a claimer...
        # ---
        for key in place:
            node = place[key]
            # If we got a sub-tree/branch, recurse into it.
            if isinstance(node, dict):
                result = self._search(node, dotted, data, data_type)
                # Did that find it?
                if result:
                    # Yes; return decoded result.
                    return result
                else:
                    # No; done with this - go to next node.
                    continue

            # If we got a leaf node, check it.
            if not issubclass(node, Encodable):
                self._log_warning(
                    "Unexpected node in registry... expect either "
                    f"strings or Encodables, got: {node}")
                continue

            # Do they claim this?
            claiming, _, _ = node.claim(data)
            # claiming, claim, reason = node.claim(data)
            if claiming:
                # Yes; return decoded result.
                return node

            # Else, not this; continue looking.

        # ---
        # Nothing found.
        # ---
        return None
