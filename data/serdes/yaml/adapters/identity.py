# coding: utf-8

'''
YAML library subclasses for encoding identities.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

import yaml

from veredi                          import log
from veredi.base.identity            import MonotonicId, SerializableId
from ..exceptions                    import (VerediYamlSerializeError,
                                             VerediYamlDeserializeError)
from ..                              import tags
from ..                              import registry

# ---
# Serializable IDs
# ---
from veredi.interface.input.identity import InputId
from veredi.data.identity            import UserId, UserKey


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# MonotonicId: Error-on-Read/Error-on-Write
# -----------------------------------------------------------------------------

# ------------------------------
# Constructor == Reader
# ------------------------------

def monotonic_id_constructor(loader: yaml.SafeLoader,
                             node:   yaml.nodes.Node) -> MonotonicId:
    '''
    Just raise Error. Should not get MonotonicId.
    '''
    msg = f"Shouldn't be decoding a MonotonicId? Found: {node}"
    error = VerediYamlDeserializeError(msg)
    raise log.exception(error, msg)


# ------------------------------
# Representer == Writer
# ------------------------------

def monotonic_id_representer(dumper: yaml.SafeDumper,
                             mid:    MonotonicId) -> yaml.nodes.Node:
    '''
    Error on MonotonicId - shouldn't get read/written.
    '''
    msg = f"Shouldn't be encoding a MonotonicId? Found: {mid}"
    error = VerediYamlSerializeError(msg)
    raise log.exception(error, msg)


# ------------------------------
# Register MonotonicId! As Unusable? *shrug*
# ------------------------------

registry.register('mid', MonotonicId,
                  monotonic_id_constructor,
                  monotonic_id_representer)


# -----------------------------------------------------------------------------
# SerializableId: Read/Write
# -----------------------------------------------------------------------------

# ------------------------------
# Constructor == Reader
# ------------------------------

def serializable_id_constructor(loader: yaml.SafeLoader,
                                node:   yaml.nodes.Node) -> SerializableId:
    '''
    Generic version.
    '''
    log.debug(f'Load this SerializableId: {node}')

    ident_map = loader.construct_mapping(node)
    klass = None
    for key in ident_map:
        klass = tags.get_class(key)
        if klass and isinstance(klass, SerializableId):
            break

    if not klass:
        msg = ("Couldn't find a SerializableId id sub-class to "
               f"construct for this node: {node}")
        error = VerediYamlDeserializeError(msg)
        raise log.exception(error, msg)

    instance = klass.deserialize(ident_map)
    return instance


# ------------------------------
# Representer == Writer
# ------------------------------

def serializable_id_representer(dumper: yaml.SafeDumper,
                                ident:  SerializableId) -> yaml.nodes.Node:
    '''
    Dump out a representation of a SerializableId.
    '''
    log.debug(f'Dump this SerializableId: {ident}')

    yaml_tag = tags.get_tag(ident.__class__)
    if not yaml_tag:
        msg = ("Couldn't find a SerializableId yaml tag to "
               f"construct for this: {ident}")
        error = VerediYamlSerializeError(msg)
        raise log.exception(error, msg)

    # Claim '!id' tag as generic SerializableId. Specific ids will have their
    # type in the serialize() return so we'll be able to deserialize with just
    # this. Plus we have implicit resolvers too.

    log.debug(f'Dump this SerializableId: {ident}')
    return dumper.represent_mapping(yaml_tag,
                                    ident.serialize(None))


# ------------------------------
# Register SerializableIDs!
# ------------------------------

# TODO: is this different kind of reg or should it use new registrar base class
# too?
registry.register(UserId._ENCODE_FIELD_NAME, UserId,
                  serializable_id_constructor,
                  serializable_id_representer,
                  UserId._get_decode_rx())


registry.register(UserKey._ENCODE_FIELD_NAME, UserKey,
                  serializable_id_constructor,
                  serializable_id_representer,
                  UserKey._get_decode_rx())


registry.register(InputId._ENCODE_FIELD_NAME, InputId,
                  serializable_id_constructor,
                  serializable_id_representer,
                  InputId._get_decode_rx())
