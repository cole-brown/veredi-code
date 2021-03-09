# coding: utf-8

'''
All your Exceptions are belong to these classes.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

# Python

# Our Stuff
from veredi.base.exceptions import VerediError


# -----------------------------------------------------------------------------
# Exceptions
# -----------------------------------------------------------------------------

class RegistryError(VerediError):
    '''
    Error getting something into or out of our registry.
    '''
    ...


class LoadError(VerediError):
    '''
    Error loading data in some way.
    '''
    ...


class SaveError(VerediError):
    '''
    Error saving data in some way.
    '''
    ...


class ReadError(VerediError):
    '''
    Error reading data in some way.
    '''
    ...


class WriteError(VerediError):
    '''
    Error writing data in some way.
    '''
    ...


class ConfigError(VerediError):
    '''
    Error during configuration set-up, or during a system's set-up when
    expecting configuration to provide something that it didn't.
    '''
    ...


class DataNotPresentError(VerediError):
    '''
    Data error. No data?
    '''
    ...


class DataRestrictedError(VerediError):
    '''
    Data error. No data for you?
    '''
    ...


class DataRequirementsError(VerediError):
    '''
    Data error. Data failed requirements?
    '''
    ...


class EncodableError(VerediError):
    '''
    An Encodable failed to encode or decode properly.
    '''
    ...


class SerializableError(VerediError):
    '''
    An Serializable failed to serialize or deserialize properly.
    '''
    ...
