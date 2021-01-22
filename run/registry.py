# coding: utf-8

'''
Set up the registries.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from types import ModuleType


import inspect
import importlib


from veredi.logger             import log
from veredi.base               import label

# Configuration Stuff
from veredi.data.config.config import Configuration
from veredi.data.exceptions    import ConfigError


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

_DOTTED = "veredi.run.registry"


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

def registries(configuration: Configuration) -> None:
    '''
    Make sure Veredi's required registries exist and have Veredi's required
    registered classes/functions/etc in them.
    '''
    log_dotted = label.join(_DOTTED, 'load')
    log.start_up(log_dotted,
                 "Importing and loading registries, registrars, "
                 "and registrations...")

    # ---
    # Sanity.
    # ---
    if not configuration:
        msg = "Configuration must be provided."
        error = ConfigError(msg,
                            data={
                                'configuration': str(configuration),
                            })
        raise log.exception(error, msg)

    # ---
    # Load Registries.
    # ---
    log.start_up(log_dotted,
                 "Importing Veredi Registries...")

    # TODO: load based on what's in configuration?

    # Import the veredi config registry.
    _import('veredi.data.config.registry', log_dotted)

    # Import the serdes packages so all the derived serdes (yaml, json, etc)
    # register.
    _import('veredi.data.serdes', log_dotted)

    # ---
    # Registration
    # ---
    log.start_up(log_dotted,
                 "Registering Veredi Classes to their Registries...")

    # Import some packages so they can register with their registries.
    _import('veredi.data.codec.encodable', log_dotted)
    # Does that work? Or must I do this?
    # ...Or put it in its own file, which I probably should do anyways maybe?
    # _import('veredi.data.codec.encodable', log_dotted)  # EncodableRegistry

    # Let Rules register stuff.
    _import('veredi.rules', log_dotted)

    # TODO: Move the specifics to math's __init__?
    _import('veredi.math.d20.parser', log_dotted)

    # ---
    # Done.
    # ---
    log.start_up(log_dotted,
                 "Done importing and loading registries, registrars, "
                 "and registrations.",
                 log_success=log.SuccessType.SUCCESS)


def _import(module: str, log_dotted: str) -> ModuleType:
    '''
    Tries to import module by `name`.

    Logs to start-up group on success/failure.

    If failure, an exception of whatever type will be allowed to bubble up.
    '''
    try:
        log.start_up(log_dotted,
                     f"Importing {module}...")
        imported = importlib.import_module(module)
        log.start_up(log_dotted,
                     f"Imported {module}: {imported}",
                     log_success=(log.SuccessType.SUCCESS
                                  if imported else
                                  log.SuccessType.FAILURE))
        return imported

    except ModuleNotFoundError as error:
        log.start_up(log_dotted,
                     f"Failed to import {module}: {error}",
                     log_success=log.SuccessType.FAILURE)
        raise

    return None
