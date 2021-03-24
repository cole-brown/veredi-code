# coding: utf-8

'''
Set up the registries.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    Optional, Union, Any, NewType, Callable,
                    Tuple, Set, List, Dict)
from veredi.base.null import Nullable, Null, null_or_none
from types import ModuleType
if TYPE_CHECKING:
    from veredi.data.config.context import ConfigContext


import os
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

_REGISTRAR_INIT_NAME: str = 'registrar'
'''
The word used for the registrar filename.
'''


_REGISTRAR_INIT_MODULE_NAME: str = f'__{_REGISTRAR_INIT_NAME}__'
'''
The module name (filename sans extension) to look for for registrars,
registries, and registrees.
'''


_REGISTRAR_INIT_UT_MODULE_NAME: str = f'__{_REGISTRAR_INIT_NAME}_ut__'
'''
If in unit-testing mode (according to background.testing.get_unit_testing()),
these files will also be searched for and imported.
'''


_REGISTREE_INIT_NAME: str = 'register'
'''
The word used for the registree filename.
'''


_REGISTREE_INIT_MODULE_NAME: str = f'__{_REGISTREE_INIT_NAME}__'
'''
The module name (filename sans extension) to look for for registrars,
registries, and registrees.
'''


_REGISTREE_INIT_UT_MODULE_NAME: str = f'__{_REGISTREE_INIT_NAME}_ut__'
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
    # registry/registrar filename-based Ignores
    #  ---
    # Ignore anything starting with two underscores...
    # Unless it's the file we want maybe.
    re.compile(r'^__(?!('
               + _REGISTRAR_INIT_NAME
               + r'|'
               + _REGISTREE_INIT_NAME
               + r'))'),

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

    PATH_REGISTRARS_RUN = label.regularize('path.registrars.run')
    '''
    A list of filenames to look for when running (normal and testing).
    '''

    PATH_REGISTRARS_TEST = label.regularize('path.registrars.test')
    '''
    A list of filenames to look for when in testing mode.
    '''

    PATH_REGISTREES_RUN = label.regularize('path.registrees.run')
    '''
    A list of filenames to look for when running (normal and testing).
    '''

    PATH_REGISTREES_TEST = label.regularize('path.registrees.test')
    '''
    A list of filenames to look for when in testing mode.
    '''

    PATH_IGNORES = label.regularize('path.ignores')
    '''
    A list of strings and regexs to ignore during path searches.
    '''

    FORCE_TEST = label.regularize('unit-test')
    '''
    A flag to force registration of unit-testing (or force skipping of it).
    Overrides auto-detection of unit-testing that registration does.
    '''

    # ------------------------------
    # Helpers
    # ------------------------------

    def full_key(self) -> str:
        '''
        Adds root key ('registration') to its value to form a full key
        (e.g. 'registration.path.ignores').
        '''
        return label.normalize(self.KEY.value, self.value)

    @classmethod
    def _get(klass: 'ConfigRegistration',
             path:  'ConfigRegistration',
             entry: Dict[str, Any]) -> Union[str, re.Pattern]:
        '''
        Get value at end of `path` keys in `entry`.
        '''
        if not path or not path.value:
            return Null()
        for node in path.value:
            entry = entry.get(node, Null())
        return entry

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
    def path_root(klass:  'ConfigRegistration',
                  entry:  Dict[str, Any],
                  config: 'Configuration') -> Nullable[paths.Path]:
        '''
        Returns the PATH_ROOT entry of this registration entry.

        PATH_ROOT is the resolved (absolute) path to the root of the file tree
        we should search for registration.
        '''
        field = klass._get(klass.PATH_ROOT, entry)
        path = config.path(field)
        # Clean up the path if we found it.
        if path:
            if not path.is_absolute():
                path = paths.cast(os.getcwd()) / path
            path = path.resolve()
        return path

    @classmethod
    def path_run(klass:      'ConfigRegistration',
                 entry:      Dict[str, Any],
                 registrars: bool) -> Nullable[str]:
        '''
        Returns either PATH_REGISTREES_RUN or PATH_REGISTRARS_RUN, depending on
        `registrars` bool.
          - True: PATH_REGISTRARS_RUN
          - False: PATH_REGISTREES_RUN

        This key's value should be a list of filenames to look for.
        '''
        if registrars:
            return klass._get(klass.PATH_REGISTRARS_RUN, entry)
        return klass._get(klass.PATH_REGISTREES_RUN, entry)

    @classmethod
    def path_test(klass: 'ConfigRegistration',
                  entry: Dict[str, Any],
                  registrars: bool) -> Nullable[str]:
        '''
        Returns either PATH_REGISTREES_TEST or PATH_REGISTRARS_TEST, depending
        on `registrars` bool.
          - True: PATH_REGISTRARS_TEST
          - False: PATH_REGISTREES_TEST

        This key's value should be a list of filenames to look for.
        '''
        if registrars:
            return klass._get(klass.PATH_REGISTRARS_TEST, entry)
        return klass._get(klass.PATH_REGISTREES_TEST, entry)

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
    registrations = configuration.get(ConfigRegistration.KEY.value)
    if null_or_none(registrations):
        cfg_str, cfg_data = configuration.info_for_error()
        msg = ("No registration settings in configuration. "
               "Registration settings required if running registration.")
        log.group_multi(_LOG_INIT, log_dotted, msg + "\n  {}",
                        data={
                            'configuration': cfg_str,
                            'settings': cfg_data,
                        },
                        log_minimum=log.Level.ERROR,
                        log_success=False)
        error = ConfigError(msg,
                            data={
                                'configuration': str(configuration),
                                'registrations': registrations,
                            })
        raise log.exception(error, msg)

    log.group_multi(_LOG_INIT,
                    log_dotted,
                    f"{len(registrations)} registration entries to run.")
    for entry in registrations:
        # If a config exception is raised, ok. Otherwise track success/failure.
        registered, dotted = _register_entry(configuration, entry, log_dotted)

        if registered:
            successes.append(dotted)
        else:
            failures.append(dotted)

    log.group_multi(_LOG_INIT,
                    log_dotted,
                    "Registration completed.\n"
                    f"  Attempted: {len(registrations)}\n"
                    f"  Succeeded: {len(successes)}\n"
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
    root = ConfigRegistration.path_root(entry, configuration)
    if not root:
        # If no root supplied, we must be dealing with ourself - otherwise no
        # idea what to do.
        if (name.lower() != VEREDI_NAME_CODE
                or dotted.lower() != VEREDI_NAME_CODE):
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
    registrars = (ConfigRegistration.path_run(entry, True) or None)
    registrars_ut = (ConfigRegistration.path_test(entry, True) or None)
    registrees = (ConfigRegistration.path_run(entry, False) or None)
    registrees_ut = (ConfigRegistration.path_test(entry, False) or None)
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
                        'registrars': registrars,
                        'registrars_test': registrars_ut,
                        'registrees': registrees,
                        'registrees_test': registrees_ut,
                        'ignores': ignores,
                        'unit-test': find_ut,
                    })

    # ---
    # Search w/ settings.
    # ---
    log.group_multi(_LOG_INIT,
                    log_dotted,
                    "Searching {} ({}) for registration...\n"
                    "  root: {}",
                    name, dotted, root)

    module_names = _find_modules(root,
                                 registrars, registrars_ut,
                                 registrees, registrees_ut,
                                 log_dotted, ignores, find_ut)
    registrar_names, registree_names = module_names

    # TODO v://future/2021-03-14T12:27:54
    # add registrar_names & registree_names to log.
    log.group_multi(_LOG_INIT,
                    log_dotted,
                    f"{len(registrar_names)} registrar "
                    f"{text.plural(registrar_names, 'module')} "
                    f"found for {name} ({dotted}).")
    log.group_multi(_LOG_INIT,
                    log_dotted,
                    f"{len(registree_names)} registree "
                    f"{text.plural(registree_names, 'module')} "
                    f"found for {name} ({dotted}).")

    # ---
    # Load all registry modules.
    # ---
    # Now load the modules we found.
    log.group_multi(_LOG_INIT,
                    log_dotted,
                    f"Loading {name} ({dotted}) registrar modules...")
    imported = []
    for name in registrar_names:
        imported.append(_import(name, log_dotted))

    for name in registree_names:
        imported.append(_import(name, log_dotted))

    log.group_multi(_LOG_INIT,
                    log_dotted,
                    f"{len(imported)} "
                    f"{text.plural(imported, 'module')} "
                    f"imported for {name} ({dotted}).")

    # If we imported nothing... that's probably a fail.
    if len(imported) <= 0:
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
    module_successes = []
    module_failures = []
    module_noop = []
    for module in imported:
        module_set_up = None
        try:
            module_set_up = getattr(module, _REGISTRATION_FUNC_NAME)
        except AttributeError:
            pass
        if not module_set_up:
            module_noop.append(module.__name__)
            continue

        log.group_multi(
            _LOG_INIT,
            log_dotted,
            f"Running `{module.__name__}.{_REGISTRATION_FUNC_NAME}()`...")

        # Call registration function with config.
        success = module_set_up(configuration, context)
        if success:
            module_successes.append(module.__name__)
        else:
            module_failures.append(module.__name__)

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
    # We'll assume that no module failures is success.
    return (len(module_failures) == 0), dotted


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
        log.group_multi(_LOG_INIT,
                        log_dotted,
                        f"Importing {module}...")
        imported = importlib.import_module(module)
        log.group_multi(_LOG_INIT,
                        log_dotted,
                        f"Imported {module}: {imported}",
                        log_success=(log.SuccessType.SUCCESS
                                  if imported else
                                     log.SuccessType.FAILURE))
        return imported

    except ModuleNotFoundError as error:
        log.group_multi(_LOG_INIT,
                        log_dotted,
                        f"Failed to import {module}: {error}",
                        log_success=log.SuccessType.FAILURE)
        raise

    return None


# -----------------------------------------------------------------------------
# Smart Importing?
# -----------------------------------------------------------------------------

def _find_modules(root:          paths.Path,
                  registrars:    List[str]                             = [],
                  registrars_ut: List[str]                             = [],
                  registrees:    List[str]                             = [],
                  registrees_ut: List[str]                             = [],
                  log_dotted:    Optional[label.DotStr]                = None,
                  ignores:       Optional[Set[Union[str, re.Pattern]]] = None,
                  find_ut:       Optional[bool]                        = None,
                  ) -> Tuple[List[str], List[str]]:
    '''
    Finds all modules in `root` and subdirectories that match our
    requirements for being a place to put "Register me plz!!!" code for
    registry entries.

    `registrees` will be set to `[_REGISTREE_INIT_MODULE_NAME]` if not
    provided. String must match file-name-sans-extension exactly.

    `registrees_ut` will be set to `[_REGISTREE_INIT_UT_MODULE_NAME]` if not
    provided. String must match file-name-sans-extension exactly.
      - This can be disabled if `find_ut` is set explicitly to False, or forced
        to be enabled if `find_ut` is set explicitly to True. The default value
        of `None` will obey the `background.testing.get_unit_testing()` flag.

    `registrars` will be set to `[_REGISTRAR_INIT_MODULE_NAME]` if not
    provided. String must match file-name-sans-extension exactly.

    `registrars_ut` will be set to `[_REGISTRAR_INIT_UT_MODULE_NAME]` if not
    provided. String must match file-name-sans-extension exactly.
      - This can be disabled if `find_ut` is set explicitly to False, or forced
        to be enabled if `find_ut` is set explicitly to True. The default value
        of `None` will obey the `background.testing.get_unit_testing()` flag.

    `log_dotted` is only used for logging and will be
    `{_DOTTED}._find_modules' if not provided.

    Returns a 2-tuple of lists of strings of module names:
      - Tuple is:
        - Tuple[0]: Registrars found.
        - Tuple[1]: Registrees found.
      - Each tuple item is a list of strings, e.g.:
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
    import_registrars = registrars
    if not registrars:
        # Can put this in imports directly - will always want it.
        import_registrars.append(_REGISTRAR_INIT_MODULE_NAME)
    if not registrars_ut:
        registrars_ut.append(_REGISTRAR_INIT_UT_MODULE_NAME)

    import_registrees = registrees
    if not registrees:
        # Can put this in imports directly - will always want it.
        import_registrees.append(_REGISTREE_INIT_MODULE_NAME)
    if not registrars_ut:
        registrees_ut.append(_REGISTREE_INIT_UT_MODULE_NAME)

    if find_ut is True:
        # Explicitly want to find unit-test class registrations.
        import_registrars.extend(registrars_ut)
        import_registrees.extend(registrees_ut)
    elif find_ut is False:
        # Explicitly /do not/ want to find unit-test class registrations.
        pass
    elif background.testing.get_unit_testing():
        # Implicitly want to find unit-test class registrations - we're in
        # unit-testing run mode.
        import_registrars.extend(registrars_ut)
        import_registrees.extend(registrees_ut)
    # Else, implicitly don't want unit-testing - we're a normal run.

    ignores = ignores or _FIND_MODULE_IGNORES

    package_path = root
    package_name = package_path.name

    # ------------------------------
    # Validate the root.
    # ------------------------------

    if root.exists():
        if root.is_dir():
            log.group_multi(_LOG_INIT,
                            log_dotted,
                            "Find module root is valid.\n"
                            "  package: {}\n"
                            "     path: {}\n"
                            "  find: \n"
                            "    registrars: {}\n"
                            "    registrees: {}",
                            package_name, package_path,
                            import_registrars, import_registrees)
        else:
            log.group_multi(_LOG_INIT,
                            log_dotted,
                            "Find module root is not a directory!\n"
                            "  package: {}\n"
                            "     path: {}\n"
                            "  find: \n"
                            "    registrars: {}\n"
                            "    registrees: {}",
                            package_name, package_path,
                            import_registrars, import_registrees,
                            log_minimum=log.Level.ERROR)
            msg = "Find module root is not a directory!"
            data = {
                'root': root,
                'registrars': registrars,
                'registrars-unit-test': registrars_ut,
                'registrees': registrees,
                'registrees-unit-test': registrees_ut,
                'ignores': ignores,
                'import_registrars': import_registrars,
                'import_registrees': import_registrees,
                'package_path': package_path,
                'package_name': package_name,
            }
            error = NotADirectoryError(msg, data)
            raise log.exception(error, msg)

    else:
        log.group_multi(_LOG_INIT,
                        log_dotted,
                        "Find module root does not exist!\n"
                        "  package: {}\n"
                        "     path: {}\n"
                        "  find: \n"
                        "    registrars: {}\n"
                        "    registrees: {}",
                        package_name, package_path,
                        import_registrars, import_registrees,
                        log_minimum=log.Level.ERROR)
        msg = "Find module root does not exist!"
        data = {
            'root': root,
            'registrars': registrars,
            'registrars-unit-test': registrars_ut,
            'registrees': registrees,
            'registrees-unit-test': registrees_ut,
            'ignores': ignores,
            'import_registrars': import_registrars,
            'import_registrees': import_registrees,
            'package_path': package_path,
            'package_name': package_name,
        }
        error = NotADirectoryError(msg, data)
        raise log.exception(error, msg)

    # ------------------------------
    # Find the modules.
    # ------------------------------

    # Idea from https://stackoverflow.com/a/5135444/425816
    export_registrars = []
    export_registrees = []

    # Get package info from root path.
    log.group_multi(_LOG_INIT,
                    log_dotted,
                    "Finding modules...\n"
                    "  unit-testing?: {}\n"
                    "        package: {}\n"
                    "           path: {}\n"
                    "  find: \n"
                    "     registrars: {}\n"
                    "     registrees: {}",
                    find_ut, package_name, package_path,
                    import_registrars, import_registrees)

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
            log.group_multi(_LOG_INIT,
                            log_dotted,
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
            log.group_multi(_LOG_INIT,
                            log_dotted,
                            "Adding sub-module to process: {}\n"
                            "    path: {}\n"
                            "  module: {}",
                            subpackage, module_relative, module_name,
                            log_minimum=log.Level.DEBUG)
            # Add them to our list of paths still to do.
            paths_to_process.extend(list(path.iterdir()))

        # Only import exactly our module name.
        elif (module_name not in import_registrars
              and module_name not in import_registrees):
            log.group_multi(_LOG_INIT,
                            log_dotted,
                            "Ignoring sub-module to process: {}\n"
                            "    path: {}\n"
                            "  module: {}\n"
                            "  reason: no filename match",
                            subpackage, module_relative, module_name,
                            log_minimum=log.Level.DEBUG)
            continue

        # Import the match only if it's the correct file type.
        elif not path.is_file():
            log.group_multi(_LOG_INIT,
                            log_dotted,
                            "Ignoring (matching): {}\n"
                            "    path: {}\n"
                            "  module: {}\n"
                            "  reason: Not a file.",
                            subpackage, module_relative, module_name,
                            log_minimum=log.Level.DEBUG)
            continue

        elif module_ext not in ('.py', '.pyw'):
            log.group_multi(_LOG_INIT,
                            log_dotted,
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
            if module_name in import_registrars:
                export_registrars.append(subpackage)
            else:
                export_registrees.append(subpackage)
            log.group_multi(_LOG_INIT,
                            log_dotted,
                            "Found matching module: {}\n"
                            "    path: {}\n"
                            "  module: {}"
                            + ("\n     ext: {}" if module_ext else ""),
                            subpackage, module_relative,
                            module_name, module_ext,
                            log_minimum=log.Level.INFO)

    if export_registrars and log.will_output(log.Group.START_UP):
        package_log = []
        for package in export_registrars:
            package_log.append("    - " + package)
        log.group_multi(_LOG_INIT,
                        log_dotted,
                        "Done finding registrar modules.\n"
                        "  package: {}\n"
                        "  matches: {}\n"
                        "{}",
                        package_name, len(export_registrars),
                        '\n'.join(package_log))

    if export_registrees and log.will_output(log.Group.START_UP):
        package_log = []
        for package in export_registrees:
            package_log.append("    - " + package)
        log.group_multi(_LOG_INIT,
                        log_dotted,
                        "Done finding registree modules.\n"
                        "  package: {}\n"
                        "  matches: {}\n"
                        "{}",
                        package_name, len(export_registrees),
                        '\n'.join(package_log))
    return (export_registrars, export_registrees)
