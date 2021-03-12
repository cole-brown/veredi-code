# coding: utf-8

'''
Registry for Encodables.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (Optional, Any, Type, Iterable, Dict)
from veredi.base.null import Null, null_to_none


from veredi.logs           import log
from veredi.base.strings   import pretty
from veredi.base.registrar import CallRegistrar, RegisterType
from veredi.base.strings   import label
from veredi.base           import numbers

from .const                import EncodedComplex, EncodedSimple, EncodedEither
from .encodable            import Encodable
from .simple               import EncodableShim


# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = [
    # ------------------------------
    # Imported
    # ------------------------------
    # Users of Encodable/EncodableRegistry want to use this a lot.
    # Export so they don't have to import from the base registrar.
    'RegisterType',

    # ------------------------------
    # File-Local
    # ------------------------------

    # ---
    # Types
    # ---
    'EncodedComplex',
    'EncodedSimple',
    'EncodedEither',
    'EncodableShim',

    # ---
    # Classes
    # ---
    'EncodableRegistry',
]


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def register(klass:  'Encodable',
             dotted: Optional[label.LabelInput] = None) -> None:
    '''
    Register the `klass` with the `dotted` string to our registry.
    '''
    # ---
    # Sanity
    # ---
    if not dotted:
        # No dotted string is an error.
        msg = ("Encodable sub-classes must be registered with a `dotted` "
               f"parameter. Got: '{dotted}'")
        error = ValueError(msg, klass, dotted)
        log.registration(dotted, msg)
        raise log.exception(error, msg)

    if dotted == klass._DO_NOT_REGISTER:
        # A 'do not register' dotted string probably means a base class is
        # encodable but shouldn't exist on its own; subclasses should
        # register themselves.
        log.registration(dotted,
                         f"Ignoring '{klass}'. "
                         "It is marked as 'do not register'.")
        return

    # ---
    # Register
    # ---
    dotted_str = label.normalize(dotted)
    log.registration(dotted,
                     f"EncodableRegistry: Registering '{dotted_str}' "
                     f"to '{klass.__name__}'...")

    dotted_args = label.regularize(dotted)
    EncodableRegistry.register(klass, *dotted_args)

    log.registration(dotted,
                     f"EncodableRegistry: Registered '{dotted_str}' "
                     f"to '{klass.__name__}'.")


def ignore(klass: 'Encodable') -> None:
    '''
    For flagging an Encodable class as one that is a base class
    or should not be registered for some other reason.
    '''
    log.registration(EncodableRegistry.dotted(),
                     f"EncodableRegistry: Marking '{klass}' "
                     f"as ignored for registration.")

    EncodableRegistry.ignore(klass)

    log.registration(EncodableRegistry.dotted(),
                     f"EncodableRegistry: '{klass}' "
                     f"marked as ignored.")


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

    @classmethod
    def _init_register(klass:     'EncodableRegistry',
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
            raise log.exception(error, msg)

        return True

    # -------------------------------------------------------------------------
    # Registration
    # -------------------------------------------------------------------------

    @classmethod
    def _register(klass:      'EncodableRegistry',
                  encodable:  Type[Encodable],
                  # *args passed into register()
                  reg_args:   Iterable[str],
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
        `reg_ours` is the place in klass._REGISTRY we placed this registration.
        `reg_bg` is the place in the background we placed this registration.
        '''
        # Get it's type field name.
        try:
            name = encodable.type_field()
        except NotImplementedError as error:
            msg = (f"{klass.__name__}._register: '{type(encodable)}' "
                   f"(\"{label.regularize(*reg_args)}\") needs to "
                   "implement type_field() function.")
            log.exception(error, msg)
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

    @classmethod
    def get(klass: 'EncodableRegistry',
            data: Optional[EncodedEither],
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

        log.debug(f"EncodableRegistry.get: data: {type(data)}, "
                  f"dotted: {dotted}, data_type: {data_type}")

        registree = None

        # ---
        # Too simple?
        # ---
        if isinstance(data, (str, *numbers.NumberTypesTuple)):
            return EncodableShim

        # ---
        # Use dotted name?
        # ---
        if dotted:
            registree = klass.get_by_dotted(dotted, None)

        # ---
        # Search for registered Encodable.
        # ---
        else:
            registry = klass._get()
            data_dotted = label.from_map(data, error_squelch=True)
            registree = klass._search(registry,
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
                log.debug(f"EncodableRegistry.get: Found registree for data, "
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
        msg = (f"{klass.__name__}: No registered Encodable found for "
               f"data. data_dotted: {data_dotted}")
        extra = (", \n"
                 "registry:\n"
                 "{}\n\n"
                 "data:\n"
                 "{}\n\n")
        error = ValueError(msg, data, registree)
        if error_squelch:
            raise error
        raise log.exception(error, msg + extra,
                            pretty.indented(registry),
                            pretty.indented(data))

    @classmethod
    def _search(klass:     'EncodableRegistry',
                place:     Dict[str, Any],
                dotted:    label.DotStr,
                data:      EncodedEither,
                data_type: Type[Encodable]) -> Optional[Encodable]:
        '''
        Provide `self._get()` as starting point of search.

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
        if label.is_dotstr(dotted):
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
                result = klass._search(node, dotted, data, data_type)
                # Did that find it?
                if result:
                    # Yes; return decoded result.
                    return result
                else:
                    # No; done with this - go to next node.
                    continue

            # If we got a leaf node, check it.
            if not issubclass(node, Encodable):
                log.warning("Unexpected node in registry... expect either "
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
