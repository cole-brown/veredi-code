# coding: utf-8

'''
Keys for accessing Configuration Data.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Type, Any, Dict
import enum

from veredi.logger import log

from .. import exceptions


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

@enum.unique
class Document(enum.Enum):
    INVALID = None
    METADATA = 'metadata'
    CONFIG = 'configuration'
    # etc...

    def get(string: str) -> Optional['Document']:
        '''
        Convert a string into a Document enum value. Returns None if no
        conversion is found. Isn't smart - no case insensitivity or anything.
        Only compares input against our enum /values/.
        '''
        for each in Document:
            if string == each.value:
                return each
        return None

    def hierarchy(doc_type: 'Document') -> 'Hierarchy':
        '''
        Gets the Hierarchy sub-class for the `doc_type`.
        '''
        if doc_type is Document.INVALID:
            error = NameError(
                "Document.INVALID has no hierarchy class.")
            raise log.exception(
                error,
                exceptions.ConfigError,
                "Should never be looking for INVALID document type.")

        elif doc_type is Document.METADATA:
            return MetadataHierarchy

        elif doc_type is Document.CONFIG:
            return ConfigHierarchy

        else:
            error = NameError(
                "Unknown document type - cannot get hierarchy class.",
                doc_type)
            raise log.exception(
                error,
                exceptions.ConfigError,
                "No case check for Document type: {}", doc_type)


@enum.unique
class Info(enum.Flag):
    LEAF = enum.auto()


# -----------------------------------------------------------------------------
# Base Class
# -----------------------------------------------------------------------------

class Hierarchy:
    '''
    Stores expected layout/hierarchy of a configuration or other data document.
    '''

    # ---
    # Class Constants
    # ---

    VKEY_DOC_TYPE = 'doc-type'
    _VIRTUAL_KEYS = {
        VKEY_DOC_TYPE: Info.LEAF
    }
    '''
    These will be in every Document Hierarchy, placed there by the Serdes when
    decoded. They do not exist when encoded/on disk/etc.
    '''

    _KEYS = None
    '''
    These are the actual keys and must be defined by sub-classes.
    '''

    # -------------------------------------------------------------------------
    # Functions
    # -------------------------------------------------------------------------

    @classmethod
    def sanity(klass: Type['Hierarchy']) -> None:
        '''
        Not much currently...
        '''
        if klass._KEYS is None:
            error = NameError(
                "Hierarchy subclass should have '_KEYS' class variable.")
            raise log.exception(error,
                                exceptions.ConfigError,
                                "{}._KEYS is None and shouldn't be.",
                                klass.__name__)

    @classmethod
    def valid(klass: Type['Hierarchy'], *keychain: str) -> bool:
        '''
        Returns True if keychain walk defined by `*keychain` is valid for
        layout defined by class' _KEYS.
        '''
        try:
            klass.sanity()
        except exceptions.ConfigError:
            # Ran face first into a cliff. Ow.
            return False

        if klass._valid_for_keys(klass._VIRTUAL_KEYS, *keychain):
            # Is a virtual key, so yes; ok.
            return True

        # Else it should be in the actual keys.
        return klass._valid_for_keys(klass._KEYS, *keychain)

    @classmethod
    def _valid_for_keys(klass: Type['Hierarchy'],
                        keyring: Dict[str, Any],
                        *keychain: str) -> bool:
        node = keyring
        for key in keychain:
            node = node.get(key, None)
            if node is None:
                # Falling off a cliff now... goodbye.
                return False

        # We walked the whole way without falling off a cliff; good job.
        return True


# -----------------------------------------------------------------------------
# Meta-Data
# -----------------------------------------------------------------------------

class MetadataHierarchy(Hierarchy):
    '''Key Hierarchy for Metadata Document.'''

    # Our data's layout.
    _KEYS = {
        'record-type': Info.LEAF,
        'version': Info.LEAF,

        'source': Info.LEAF,
        'author': Info.LEAF,
        'date':   Info.LEAF,

        'system': Info.LEAF,
        'name': Info.LEAF,
        'display-name': Info.LEAF,
    }
    '''
    Layout of metadata document.
    '''


# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

class ConfigHierarchy(Hierarchy):
    '''Key Hierarchy for Configuration Document.'''

    # Our data's layout.
    _KEYS = {
        'data': {
            'repository': {
                'type': Info.LEAF,
                'directory': Info.LEAF,
                'sanitize': Info.LEAF,
            },
            'serdes': Info.LEAF,
        },

        'rules': {
            'type': Info.LEAF,
            'ability': Info.LEAF,
            'health': Info.LEAF,
            'movement': Info.LEAF,
            'skill': Info.LEAF,
            'combat': {
                'attack': Info.LEAF,
                'defense': Info.LEAF,
            },
        },

        'engine': {
            'systems': Info.LEAF,
            'time': {
                'timeouts': {
                    'default': Info.LEAF,
                    'genesis': Info.LEAF,
                    'intrasystem': Info.LEAF,
                    'apoptosis': Info.LEAF,
                    'apocalypse': Info.LEAF,
                },
            },
        },

        'server': {
            'mediator': {
                'type': Info.LEAF,
                'serdes': Info.LEAF,
                'hostname': Info.LEAF,
                'port': Info.LEAF,
                'ssl': Info.LEAF,
            },

            'input': {
                'type': Info.LEAF,
                'command': Info.LEAF,
                'history': Info.LEAF,
                'parser': {
                    'math': Info.LEAF,
                },
            },

            'output': {
                'type': Info.LEAF,
            },
        },

        'client': {
            'mediator': {
                'type': Info.LEAF,
                'serdes': Info.LEAF,
                'hostname': Info.LEAF,
                'port': Info.LEAF,
                'ssl': Info.LEAF,
            },
        },
    }
    '''
    Layout of configuration document.
    '''
