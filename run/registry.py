# coding: utf-8

'''
Set up the registries.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Union, Iterable, Set
from types import ModuleType


import os
import inspect
import importlib
import re


from veredi.logs               import log
from veredi.base               import paths
from veredi.base.strings       import label, text

# Configuration Stuff
from veredi.data.config.config import Configuration
from veredi.data.exceptions    import ConfigError


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

_DOTTED = 'veredi.run.registry'


_REGISTRATION_INIT_NAME = 'register'
'''
The word used for the registration filename.
'''

_REGISTRATION_INIT_MODULE_NAME = f'__{_REGISTRATION_INIT_NAME}__'
'''
The module name (filename sans extension) to look for for registrars,
registries, and registrees.
'''


_FIND_MODULE_IGNORES = set({
    # ---
    # General Ignores
    # ---
    '.git',
    '__pycache__',
    re.compile(r'^__LICENSE.*'),  # __LICENSE__, __LICENSES__
    '__templates__',

    #  ---
    # `_REGISTRATION_INIT_FILE_NAME`-based Ignores
    #  ---
    # Ignore anything starting with two underscores...
    # Unless it's the file we want maybe.
    re.compile(r'^__(?!' + _REGISTRATION_INIT_NAME + r')'),

    # And, because our _REGISTRATION_INIT_FILE_NAME /does/ start with two
    # underscores, we can also ignore everything that /doesn't/ start with
    # exactly two underscores.
    #   re.compile(r'^(?!__).*'),
    # NOTE: No. There are things called 'directories', turns out... And turns
    # out we need to walk down into those to look for our files.

    # ---
    # Veredi Ignores
    # ---
    # Don't care about testing directory.
    'zest',
    # Run module should be for getting things running; things that need to
    # register should be elsewhere?
    'run',
})
'''
A set of either exact strings to match to filenames (without parent path or
extension), or compiled regex patterns to match to path names.

NOTE: Regexs must return a match for strings they /do/ want to ignore.
'''


# -----------------------------------------------------------------------------
# Initialize Registries
# -----------------------------------------------------------------------------

def registrars(configuration: Configuration) -> None:
    '''
    Make sure Veredi's required registries/registrars exist and have Veredi's
    required registered classes/functions/etc in them.
    '''
    log_dotted = label.normalize(_DOTTED, 'registrars')
    log.start_up(log_dotted,
                 "Importing and loading registries & registrars...")

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
                 "Importing Veredi Registries & Registrars...")

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

    # TODO: v://future/registering/2021-02-01T10:34:57-0800
    # TODO: import for registering (instead of importing registries) should happen more automaticallyish?
    _import('veredi.data.repository.file.tree', log_dotted)

    # ---
    # Done.
    # ---
    log.start_up(log_dotted,
                 "Done importing and loading registries & registrars.",
                 log_success=log.SuccessType.SUCCESS)


def registrees(configuration: Configuration,
               *start:        paths.PathsInput,
               filename:      Optional[str] = None) -> None:
    '''
    Import all registrees starting from `start` directory and checking all
    sub-directories.

    If `filename` is provided, looks for that. Otherwise looks for files that
    match the `_REGISTRATION_INIT_MODULE_NAME` constant.
    '''
    log_dotted = label.normalize(_DOTTED, 'registrees')
    log.start_up(log_dotted,
                 "Importing and loading registrees...")

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
    root = paths.cast(*start)
    log.start_up(log_dotted,
                 "Importing Veredi Registrees...\n",
                 "  from root: {}\n"
                 "  with name: {}",
                 str(root), filename)

    registree_modules = _find_modules(*start, filename, log_dotted)
    log.ultra_hyper_debug(registree_modules)

    # ---
    # Done.
    # ---

    log.start_up(log_dotted,
                 "Done importing and loading registrees.\n"
                 "{} registree {} found.",
                 len(registree_modules),
                 text.plural(registree_modules, 'module'),
                 log_success=log.SuccessType.SUCCESS)


# -----------------------------------------------------------------------------
# Importing
# -----------------------------------------------------------------------------

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


# -----------------------------------------------------------------------------
# Smart Importing?
# -----------------------------------------------------------------------------

def _find_modules(*root:     paths.PathsInput,
                  filename:   Optional[str]                         = None,
                  log_dotted: Optional[label.DotStr]                = None,
                  ignores:    Optional[Set[Union[str, re.Pattern]]] = None
                  ) -> Iterable:
    '''
    Finds all modules in `root` and subdirectories that match our
    requirements for being a place to put "Register me plz!!!" code for
    registry entries.

    `root` is one single path - can be in segments.
    For example:
      _find_modules("/path/to/jeff")
      _find_modules("/path", "to", "jeff")

    `filename` will be set to `_REGISTRATION_INIT_MODULE_NAME` if not
    provided. String must match file-name-sans-extension exactly.

    `log_dotted` is only used for logging and will be
    `{_DOTTED}._find_modules' if not provided.

    Returns a list of strings of module names:
      [
        'veredi.__register__',
        'veredi.config.__register__',
        ...
      ]
    '''
    # ------------------------------
    # Set up vars...
    # ------------------------------
    log_dotted = log_dotted or label.normalize(_DOTTED, '_find_modules')
    import_name = filename or _REGISTRATION_INIT_MODULE_NAME
    root = paths.cast(*root)
    ignores = ignores or _FIND_MODULE_IGNORES

    package_path = root
    package_name = package_path.name

    # ------------------------------
    # Validate the root.
    # ------------------------------

    if root.exists():
        if root.is_dir():
            log.start_up(log_dotted,
                         "Find module root is valid.\n"
                         "  package: {}\n"
                         "     path: {}\n"
                         "     find: {}",
                         package_name, package_path, import_name)
        else:
            log.start_up(log_dotted,
                         "Find module root is not a directory!\n"
                         "  package: {}\n"
                         "     path: {}\n"
                         "     find: {}",
                         package_name, package_path, import_name,
                         log_minimum=log.Level.ERROR)
            msg = "Find module root is not a directory!"
            data = {
                'root': root,
                'filename': filename,
                'ignores': ignores,
                'import_name': import_name,
                'package_path': package_path,
                'package_name': package_name,
            }
            error = NotADirectoryError(msg, data)
            raise log.exception(error, msg)

    else:
        log.start_up(log_dotted,
                     "Find module root does not exist!\n"
                     "  package: {}\n"
                     "     path: {}\n"
                     "     find: {}",
                     package_name, package_path, import_name,
                     log_minimum=log.Level.ERROR)
        msg = "Find module root does not exist!"
        data = {
            'root': root,
            'filename': filename,
            'ignores': ignores,
            'import_name': import_name,
            'package_path': package_path,
            'package_name': package_name,
        }
        error = NotADirectoryError(msg, data)
        raise log.exception(error, msg)

    # ------------------------------
    # Find the modules.
    # ------------------------------

    # Idea from https://stackoverflow.com/a/5135444/425816
    exports = []

    # Get package info from root path.
    log.start_up(log_dotted,
                 "Finding modules...\n"
                 "  package: {}\n"
                 "     path: {}\n"
                 "    files: {}",
                 package_name, package_path, import_name)

    # Make a list so we can keep extending it with sub-directories as we walk
    # the file tree.
    paths_to_process = list(package_path.iterdir())
    # Get all modules in package that do not match ignores...
    for path in paths_to_process:
        module_relative = path.relative_to(package_path)
        module_name = module_relative.stem
        module_ext = module_relative.suffix
        # The sub-package's name to export should be relative to our start
        # path (`package_path`) and without its file extension.
        subpackage = label.from_path(module_relative.with_suffix(''))

        # Should we ignore this?
        ignore = False
        matched_on = None
        matching = None
        for check in ignores:
            if isinstance(check, str):
                # Ignore only if full match.
                if check == module_name:
                    ignore = True
                    matched_on = "string"
                    matching = check

            elif isinstance(check, re.Pattern):
                # Ignore if regex /does/ matches.
                if check.match(module_name):
                    ignore = True
                    matched_on = "regex"
                    matching = check.pattern

            # If we've found a reason to ignore this, quit early.
            if ignore:
                break

        # This path should be ignored, so continue on.
        if ignore:
            log.start_up(log_dotted,
                         "Ignoring:\n"
                         "          path: {}\n"
                         "        module: {}\n"
                         "   ignore type: {}\n"
                         "  ignore match: {}",
                         module_relative, module_name,
                         matched_on, matching,
                         log_minimum=log.Level.DEBUG)
            continue

        # Import a sub-module directory.
        if path.is_dir():
            log.start_up(log_dotted,
                         "Adding sub-module to process: {}\n"
                         "    path: {}\n"
                         "  module: {}",
                         subpackage, module_relative, module_name,
                         log_minimum=log.Level.DEBUG)
            # Add them to our list of paths still to do.
            paths_to_process.extend(list(path.iterdir()))

        # Only import exactly our module name.
        elif module_name != import_name:
            log.start_up(log_dotted,
                         "Ignoring sub-module to process: {}\n"
                         "    path: {}\n"
                         "  module: {}\n"
                         "  reason: file name mismatch",
                         subpackage, module_relative, module_name,
                         log_minimum=log.Level.DEBUG)
            continue

        # Import the match only if it's the correct file type.
        elif not path.is_file():
            log.start_up(log_dotted,
                         "Ignoring (matching): {}\n"
                         "    path: {}\n"
                         "  module: {}\n"
                         "  reason: Not a file.",
                         subpackage, module_relative, module_name,
                         log_minimum=log.Level.DEBUG)
            continue

        elif module_ext not in ('.py', '.pyw'):
            log.start_up(log_dotted,
                         "Ignoring (matching): {}\n"
                         "    path: {}\n"
                         "  module: {}\n"
                         "  reason: Not a python module file extension "
                         "(.py, .pyw).",
                         subpackage, module_relative, module_name,
                         log_minimum=log.Level.DEBUG)
            continue

        # Alright; ran out of reasons not to import this guy.
        else:
            exports.append(subpackage)
            log.start_up(log_dotted,
                         "Found matching module: {}\n"
                         "    path: {}\n"
                         "  module: {}"
                         + ("\n     ext: {}" if module_ext else ""),
                         subpackage, module_relative, module_name, module_ext,
                         log_minimum=log.Level.INFO)

    if exports and log.will_output(log.Group.START_UP):
        package_log = []
        for package in exports:
            package_log.append("    - " + package)
        log.start_up(log_dotted,
                     "Done finding modules.\n"
                     "  package: {}\n"
                     "  matches: {}\n"
                     "{}",
                     package_name, len(exports),
                     '\n'.join(package_log))
    return exports
