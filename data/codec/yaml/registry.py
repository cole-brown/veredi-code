# coding: utf-8

'''
Helpers for registering Veredi classes to YAML libraryfor encoding/decoding.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Type, NewType, Callable, Dict, List, Tuple

import yaml
import re

from veredi.logger import log
from ...exceptions import RegistryError
from . import tags


# -----------------------------------------------------------------------------
# Types
# -----------------------------------------------------------------------------

YamlDecode = NewType('YamlDecode',
                     Callable[[yaml.SafeLoader, yaml.nodes.Node], Type])


YamlEncode = NewType('YamlEncode',
                     Callable[[yaml.SafeDumper, Type], yaml.nodes.Node])


YamlAddClassTuple = NewType(
    'YamlAddClassTuple',
    Tuple[str, Type, Optional[YamlDecode], Optional[YamlEncode]])


# -----------------------------------------------------------------------------
# Registry of YAML Tags for Veredi Things
# -----------------------------------------------------------------------------

_TAG_TO_CLASS = {}
'''Dictionary of YAML tag strings to class.'''

_CLASS_TO_TAG = {}
'''Dictionary of class to YAML tag strings.'''


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Get from registry.
# -----------------------------------------------------------------------------

def get_class(tag: str) -> Optional[Type]:
    '''
    Tries to use `tag` name to get a registered class type.
    Returns the class or None.
    '''
    return _TAG_TO_CLASS.get(tag, None)


def get_tag(klass: Type) -> Optional[str]:
    '''
    Tries to use `klass` type to get a registered tag string.
    Returns the tag or None.
    '''
    return _CLASS_TO_TAG.get(klass, None)


def get_class_all(klass: Type) -> List[Type]:
    '''
    Get all subclasses of `klass` registered and return them in a list.
    Returns an empty list if nothing found.
    '''
    subclasses_registered = []
    for key in _CLASS_TO_TAG:
        if isinstance(key, klass):
            subclasses_registered.add(key)

    return subclasses_registered


# -----------------------------------------------------------------------------
# YAML Tags / Veredi Classes Registry Functions
# -----------------------------------------------------------------------------

def _internal_register(tag: str, klass: Type) -> None:
    '''
    Add YAML `tag` / `klass` type to both tag->class and class->tag registries.
    '''
    # Just make sure they have a good tag name...
    if not tags.valid(tag):
        raise log.exception(None,
                            RegistryError,
                            "Invalid tag! YAML Tags must start with '!'. "
                            f"Got: {tag}.")

    # Prevent overwrites.
    if tag in _TAG_TO_CLASS:
        ex_klass = _TAG_TO_CLASS[tag]
        raise log.exception(None,
                            RegistryError,
                            "Tag already exists in registry. "
                            f"Existing: {tag} -> {ex_klass}. "
                            f"Requested: {tag} -> {klass}.")
    if klass in _CLASS_TO_TAG:
        ex_tag = _CLASS_TO_TAG[klass]
        raise log.exception(None,
                            RegistryError,
                            "Class already exists in registry. "
                            f"Existing: {klass} -> {ex_tag}. "
                            f"Requested: {klass} -> {tag}.")

    # Add to both registries.
    _TAG_TO_CLASS[tag] = klass
    _CLASS_TO_TAG[klass] = tag


# NOTE: YAML has no unregister, so I'm leaving this out.
# def unregister(tag:   Optional[str] = None,
#                klass: Optional[Type] = None) -> None:
#     '''
#     Unregisters tag and klass from registeries. If only one is specified,
#     tries to get the other from the registry so it can deregister both ends.
#     '''
#     if not tag:
#         tag = get_tag(klass)
#     if not klass:
#         klass = get_class(tag)

#     # Continue on even if we only got supplied one and couldn't find the
#     # other. Might as well make sure the registries are consistent for this
#     # thing.
#     #
#     # `None` is not a valid tag or class; it shouldn't be in there anyways.
#     # So just pop regardless.
#     _tag_to_class.pop(tag, None)
#     _class_to_tag.pop(klass, None)


# -----------------------------------------------------------------------------
# Veredi Class / YAML encode/decode Registry Functions
# -----------------------------------------------------------------------------

# TODO [2020-08-21]: make a property like Veredi's registry.register()?
def register(name:        str,
             klass:       Type,
             decode_fn:   Optional[YamlDecode],
             encode_fn:   Optional[YamlEncode],
             implicit_rx: Optional[re.Pattern] = None) -> None:
    '''
    Basically, register with ourself and with YAML.

    In detail:
      - Create a yaml tag from the `name` string.
      - Register tag/Type in our registry.
      - Adds `klass` to YAML representer/constructor if provided functions.
      - Checks that `klass` is a YAMLObject if not provided functions.
      - Adds an implicit resolver to YAML if provided with an `implicit_rx`
        regex Pattern.
    '''
    # ---
    # Tag
    # ---
    if tags.valid(name):
        raise log.exception(
            None,
            RegistryError,
            "Expecting string, not YAML Tag. String should not start with '!'."
            f"Got: {name} for {klass}.")

    # ---
    # Register to us.
    # ---
    # _internal_register() will check/error if invalid tag.
    tag = tags.make(name)
    _internal_register(tag, klass)

    # ---
    # Register to YAML
    # ---
    if decode_fn and encode_fn:
        yaml.add_constructor(tag,
                             decode_fn,
                             Loader=yaml.SafeLoader)
        yaml.add_representer(klass,
                             encode_fn,
                             Dumper=yaml.SafeDumper)

    elif not decode_fn and not encode_fn:
        if not isinstance(klass, yaml.YAMLObject):
            raise log.exception(
                None,
                RegistryError,
                f"Class '{klass}' must either derive from YAMLObject or "
                "provided encoder/decoder functions for YAML to use."
                f"Got: {encode_fn}, {decode_fn}.")

    else:
        raise log.exception(
            None,
            RegistryError,
            f"Class '{klass}' must either derive from YAMLObject or "
            "provided encoder/decoder functions for YAML to use."
            f"Got: {encode_fn}, {decode_fn}.")

    # They can also optionally have an implicit resolver...
    if implicit_rx:
        # This is for dump and load.
        yaml.add_implicit_resolver(tag, implicit_rx)

    log.debug(f"YAML Registry added: {name}, {klass}")
