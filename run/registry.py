# coding: utf-8

'''
Set up the registries.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    Optional, Union, Any, Callable, Iterable, Set, List, Dict)
from veredi.base.null import Nullable, Null
from types import ModuleType
if TYPE_CHECKING:
    from veredi.data.config.context import ConfigContext


import os
import inspect
import importlib
import re
import enum


from veredi.logs               import log
from veredi.base               import paths
from veredi.base.const         import (LIB_VEREDI_ROOT,
                                       VEREDI_NAME_CODE,
                                       VEREDI_NAME_DISPLAY)
from veredi.base.strings       import label, text
from veredi.data               import background

# Configuration Stuff
from veredi.data.config.config import Configuration
from veredi.data.exceptions    import ConfigError


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

_DOTTED: str = 'veredi.run.registry'


_LOG_INIT: List[log.Group] = [
    log.Group.START_UP,
    log.Group.REGISTRATION,
]
'''
Group of logs we use a lot for log.group_multi().
'''


_REGISTRATION_FUNC_NAME: str = 'run_during_registration'
'''
The name of the optional function to run for a module's initialization
after importing it.
'''


RegistrationFunc = NewType('RegistrationFunc',
                           Callable[['Configuration', 'ConfigContext'], bool])
'''
The signature expected for `_REGISTRATION_FUNC_NAME` functions.
'''

_REGISTRATION_INIT_NAME: str = 'register'
'''
The word used for the registration filename.
'''


_REGISTRATION_INIT_MODULE_NAME: str = f'__{_REGISTRATION_INIT_NAME}__'
'''
The module name (filename sans extension) to look for for registrars,
registries, and registrees.
'''


_REGISTRATION_INIT_UT_MODULE_NAME: str = f'__{_REGISTRATION_INIT_NAME}_ut__'
'''
If in unit-testing mode (according to background.testing.get_unit_testing()),
these files will also be searched for and imported.
'''


_FIND_MODULE_IGNORES: Set = set({
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

# ------------------------------
# Config Settings
# ------------------------------

@enum.unique
class ConfigRegistration(enum.Enum):
    '''
    Configuration settings keys for registration.
    '''

    KEY = 'registration'
    '''
    Registration is a list of entries for what to search for registration.
    '''

    NAME = label.regularize('register.name')
    '''
    Who is being registered.
    '''

    DOTTED = label.regularize('register.dotted')
    '''
    Who is being registered.
    '''

    PATH_ROOT = label.regularize('path.root')
    '''
    Path to resolve to get to the root of the file tree to be search for
    registration files.
    '''

    PATH_RUN = label.regularize('path.run')
    '''
    A list of filenames to look for when running (normal and testing).
    '''

    PATH_TEST = label.regularize('path.test')
    '''
    A list of filenames to look for when in testing mode.
    '''

    PATH_IGNORES = label.regularize('path.ignores')
    '''
    A list of strings and regexs to ignore during path searches.
    '''

    FORCE_TEST = label.regularlize('unit-test')
    '''
    A flag to force registration of unit-testing (or force skipping of it).
    Overrides auto-detection of unit-testing that registration does.
    '''

    # ------------------------------
    # Helpers
    # ------------------------------

    @classmethod
    def full_key(self) -> str:
        '''
        Adds root key ('registration') to its value to form a full key
        (e.g. 'registration.path.ignores').
        '''
        return label.normalize(self.KEY.value, self.value)

    @classmethod
    def _get(klass: 'ConfigRegistration',
             path:  label.DotList,
             entry: Dict[str, Any]) -> Union[str, re.Pattern]:
        '''
        Get value at end of `path` keys in `entry`.
        '''
        for node in klass.NAME:
            entry = entry.get(node, Null())

    @classmethod
    def name(klass: 'ConfigRegistration',
             entry: Dict[str, Any]) -> str:
        '''
        Returns the NAME entry of this registration entry.
        '''
        value = klass._get(klass.NAME, entry)
        return value

    @classmethod
    def dotted(klass: 'ConfigRegistration',
               entry: Dict[str, Any]) -> label.DotStr:
        '''
        Returns the DOTTED entry of this registration entry.
        '''
        value = klass._get(klass.DOTTED, entry)
        return label.normalize(value)

    @classmethod
    def path_root(klass: 'ConfigRegistration',
                  entry: Dict[str, Any]) -> Nullable[paths.Path]:
        '''
        Returns the PATH_ROOT entry of this registration entry.

        PATH_ROOT is the resolved (absolute) path to the root of the file tree
        we should search for registration.
        '''
        field = klass._get(klass.PATH_ROOT, entry)
        path = paths.cast(field, allow_none=True, allow_null=True)
        if path:
            path = path.resolve()
        return path

    @classmethod
    def path_run(klass: 'ConfigRegistration',
                 entry: Dict[str, Any]) -> Nullable[str]:
        '''
        Returns the PATH_RUN entry of this registration entry.

        PATH_RUN should be a list of filenames to look for.
        '''
        return klass._get(klass.PATH_RUN, entry)

    @classmethod
    def path_test(klass: 'ConfigRegistration',
                  entry: Dict[str, Any]) -> Nullable[str]:
        '''
        Returns the PATH_TEST entry of this registration entry.

        PATH_TEST should be a list of filenames to look for.
        '''
        return klass._get(klass.PATH_TEST, entry)

    @classmethod
    def path_ignores(klass: 'ConfigRegistration',
                     entry: Dict[str, Any]) -> Nullable[str]:
        '''
        Returns the PATH_IGNORES entry of this registration entry.

        PATH_IGNORES should be a list of strings and regexes to match
        while checking file and directory names. A matching file/dir
        will be ignored.
        '''
        return klass._get(klass.PATH_IGNORES, entry)

    @classmethod
    def force_test(klass: 'ConfigRegistration',
                   entry: Dict[str, Any]) -> Nullable[bool]:
        '''
        Returns the FORCE_TEST entry of this registration entry.

        FORCE_TEST, if it exists, should be true to force registration of
        testing classes or false to force skipping test class registration.

        Generally, not supplying is best choice - it will be auto-detected.
        '''
        return klass._get(klass.PATH_IGNORES, entry)


# -----------------------------------------------------------------------------
# Initialize Registries
# -----------------------------------------------------------------------------

def registration(configuration: Configuration) -> None:
    '''
    Searches for all of Veredi's required registries, registrars, registrees,
    and invisible elephants.

    Eagerly loads them so they are available at run-time when needed.
    '''
    log_dotted = label.normalize(_DOTTED, 'registration')
    log.group_multi(_LOG_INIT,
                    log_dotted,
                    "Importing and loading registries, "
                    "registrars & registrees...")

    # ---
    # Sanity.
    # ---
    if not configuration:
        msg = "Configuration must be provided."
        log.group_multi(_LOG_INIT, log_dotted, msg)
        error = ConfigError(msg,
                            data={
                                'configuration': str(configuration),
                            })
        raise log.exception(error, msg)

    # ---
    # Find all registry modules.
    # ---
    log.group_multi(_LOG_INIT,
                    log_dotted,
                    "Finding registry modules...")

    successes = []
    failures = []
    registrations = configuration.get(ConfigRegistration.KEY)
    for entry in registrations:
        # If a config exception is raised, ok. Otherwise track success/failure.
        registered, dotted = _register_entry(configuration, entry, log_dotted)

       if registered:
           successses.append(dotted)
       else:
           failures.append(dotted)

    log.group_multi(_LOG_INIT,
                    log_dotted,
                    "Registration completed.\n"
                    f"  Attempted: {len(registrations)}\n"
                    f"  Succeeded: {len(successses)}\n"
                    f"     Failed: {len(failures)}\n",
                    "{data}",
                    # TODO v://future/2021-03-14T12:27:54
                    # And get rid of that '\n'
                    data={
                        'success': successes,
                        'failure': failures,
                    })

    # ---
    # Done.
    # ---
    # Did we completely succeed?
    success = log.SuccessType.success_or_failure(successes, failures)
    log.group_multi(_LOG_INIT,
                    log_dotted,
                    "Done with registration importing & loading.",
                    log_success=success)


def _register_entry(configuration: Configuration,
                    entry:         Dict[str, Any],
                    log_dotted:    str) -> (bool, label.DotStr):
    '''
    Run a registration sweep for one registration entry in the configuration.
    '''

    # ---
    # Get settings...
    # ---
    # Required:
    name = ConfigRegistration.name(entry)
    dotted = ConfigRegistration.dotted(entry)
    if not name or not dotted:
        msg = (f"Invalid 'registration' entry in configuration file. "
               "At a minimum, "
               f"'{ConfigRegistration.NAME.full_key()}' and"
               f"'{ConfigRegistration.DOTTED.full_key()}'."
               f"must be provided. All non-'{VEREDI_NAME_DISPLAY}' "
               "registrations must also, at a minimum, provide: "
               f"'{ConfigRegistration.PATH_ROOT.full_key()}'.")
        log.group_multi(_LOG_INIT,
                        log_dotted,
                        msg)
        background.config.exception(None, msg,
                                    error_data={
                                        'config-reg-entry': entry,
                                    })

    log.group_multi(_LOG_INIT,
                    log_dotted,
                    f"Getting registration settings for {name} ({dotted})...")

    # Quantum Required:
    root = ConfigRegistration.path_root(entry)
    if not root:
        # If no root supplied, we must be dealing with ourself - otherwise no
        # idea what to do.
        if name.lower() != VEREDI_NAME_CODE or dotted.lower() != VEREDI_NAME_CODE:
            msg = (f"Don't know how to register {name} ({dotted}). "
                   "At a minimum, "
                   f"'{ConfigRegistration.PATH_ROOT.full_key()}' "
                   "must be provided along with "
                    f"'{ConfigRegistration.NAME.full_key()}' and"
                    f"'{ConfigRegistration.DOTTED.full_key()}'.")
            log.group_multi(_LOG_INIT,
                            log_dotted,
                            msg)
            background.config.exception(None, msg,
                                        error_data={
                                            'config-reg-entry': entry,
                                        })
        # We know a default to use for Veredi. Our root.
        else:
            root = LIB_VEREDI_ROOT

    # Optional:
    filenames = (ConfigRegistration.path_run(entry) or None)
    filenames_ut = (ConfigRegistration.path_test(entry) or None)
    ignores = (ConfigRegistration.path_ignores(entry) or None)
    find_ut = (ConfigRegistration.force_test(entry) or None)

    log.group_multi(_LOG_INIT,
                    log_dotted,
                    f"Settings for {name} ({dotted}): {{data}}",
                    # TODO v://future/2021-03-14T12:27:54
                    data={
                        'name': name,
                        'dotted': dotted,
                        'root': root,
                        'run': filenames,
                        'test': filenames_ut,
                        'ignores': ignores,
                        'unit-test': find_ut,
                    })

    # ---
    # Search w/ settings.
    # ---
    log.group_multi(_LOG_INIT,
                    log_dotted,
                    f"Searching {name} ({dotted}) for registration...")

    module_names = _find_modules(root, filenames, filenames_ut,
                                 log_dotted, ignores, find_ut)
    log.group_multi(_LOG_INIT,
                    log_dotted,
                    f"{len(module_names)} "
                    f"{text.plural(module_names, 'module')}"
                    f"found for {name} ({dotted}).")

    # ---
    # Load all registry modules.
    # ---
    # Now load the modules we found.
    log.group_multi(_LOG_INIT,
                    log_dotted,
                    f"Loading {name} ({dotted}) registry modules...")
    imported = []
    for name in module_names:
        imported.append(_import(name, log_dotted))

    log.group_multi(_LOG_INIT,
                    log_dotted,
                    f"{len(imported)} "
                    f"{text.plural(imported, 'module')}"
                    f"imported for {name} ({dotted}).")

    # If we imported nothing... that's probably a fail.
    if imported <= 0:
        return False, dotted

    # ---
    # Set-up modules?
    # ---
    # Look for the function. Call it the args defined in RegistrationFunc if it
    # exists.
    log.group_multi(_LOG_INIT,
                    log_dotted,
                    "Checking for module initialization functions "
                    f"(`{_REGISTRATION_FUNC_NAME}()`)...")

    context = configuration.make_config_context()
    module_successes = 0
    module_failures = 0
    module_noop = 0
    for module in imported:
        module_set_up = getattr(module, _REGISTRATION_FUNC_NAME)
        if not module_set_up:
            module_noop += 1
            continue

        log.group_multi(
            _LOG_INIT,
            log_dotted,
            f"Running `{module.__name__}.{_REGISTRATION_FUNC_NAME}()`...")

        # Call registration function with config.
        success = module_set_up(configuration, context)
        if success:
            module_successes += 1
        else:
            module_failures += 1

        log.group_multi(
            _LOG_INIT,
            log_dotted,
            f"`{module.__name__}.{_REGISTRATION_FUNC_NAME}()` done.",
            log_success=success)

    log.group_multi(_LOG_INIT,
                    log_dotted,
                    "Done initializing modules.",
                    data={
                        'successes': module_successes,
                        'failures':  module_failures,
                        'no-init':   module_noop,
                    })

    # ---
    # Success or Failure, and list of module names imported.
    # ---
    return (module_failures > 0), dotted


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

def _find_modules(*root:       paths.PathsInput,
                  filenames:   List[str]                             = [],
                  filename_ut: List[str]                             = [],
                  log_dotted:  Optional[label.DotStr]                = None,
                  ignores:     Optional[Set[Union[str, re.Pattern]]] = None,
                  find_ut:     Optional[bool]                        = None,
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

    `filename-ut` will be set to `_REGISTRATION_INIT_UT_MODULE_NAME` if not
    provided. String must match file-name-sans-extension exactly.
      - This can be disabled if `find_ut` is set explicitly to False, or forced
        to be enabled if `find_ut` is set explicitly to True. The default value
        of `None` will obey the `background.testing.get_unit_testing()` flag.

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

    # What should we import? Are we importing unit-testing stuff too?
    imports = filenames
    if not imports:
        imports.append(_REGISTRATION_INIT_MODULE_NAME)
    if not filenames_ut:
       filenames_ut.append(_REGISTRATION_INIT_UT_MODULE_NAME)

    if find_ut is True:
        # Explicitly want to find unit-test class registrations.
        imports.extend(filenames_ut)
    elif find_ut is False:
        # Explicitly /do not/ want to find unit-test class registrations.
        pass
    elif background.testing.get_unit_testing():
        # Implicitly want to find unit-test class registrations - we're in
        # unit-testing run mode.
        imports.extend(filenames_ut)
    # Else, implicitly don't want unit-testing - we're a normal run.

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
                         package_name, package_path, imports)
        else:
            log.start_up(log_dotted,
                         "Find module root is not a directory!\n"
                         "  package: {}\n"
                         "     path: {}\n"
                         "     find: {}",
                         package_name, package_path, imports,
                         log_minimum=log.Level.ERROR)
            msg = "Find module root is not a directory!"
            data = {
                'root': root,
                'filenames': filenames,
                'filenames-unit-test': filenames_ut,
                'ignores': ignores,
                'imports': imports,
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
                     package_name, package_path, imports,
                     log_minimum=log.Level.ERROR)
        msg = "Find module root does not exist!"
        data = {
            'root': root,
            'filenames': filenames,
            'filenames-unit-test': filenames_ut,
            'ignores': ignores,
            'imports': imports,
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
                 package_name, package_path, imports)

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
        elif module_name not in imports:
            log.start_up(log_dotted,
                         "Ignoring sub-module to process: {}\n"
                         "    path: {}\n"
                         "  module: {}\n"
                         "  reason: no filename match",
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
