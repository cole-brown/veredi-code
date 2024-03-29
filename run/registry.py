# coding: utf-8

'''
Set up the registries.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    Optional, Union, Type, Any, NewType, Callable,
                    Tuple, Set, List, Dict, Iterator)
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

_DOTTED: label.DotStr = 'veredi.run.registry'


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


_FIND_MODULE_IGNORES_DIRS: Set[Union[str, re.Pattern]] = set({
    # ---
    # Default Ignored Dirs
    # ---
    re.compile(r'.git'
               r'|__pycache__'
               r'|__LICENSES?__'
               r'|__templates__'
               r'|zest'
               r'|run'),
})
'''
A set of either exact strings to match to directory names (without parent
path or extension), or compiled regex patterns to match to full path.

NOTE: Regexs must return a search match for strings they /do/ want to ignore.
'''


_FIND_MODULE_IGNORES: Set[Union[str, re.Pattern]] = set({
    # ---
    # General Ignores
    # ---
    re.compile(r'^__LICENSE.*'),  # __LICENSE__, __LICENSES__

    # ---
    # registry/registrar filename-based Ignores
    # ---
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

    PATH_IGNORE_FILES = label.regularize('path.ignore.files')
    '''
    A list of strings and regexs of files to ignore during path searches.
    '''

    PATH_IGNORE_DIRS = label.regularize('path.ignore.directories')
    '''
    A list of strings and regexs of directories to ignore during path searches.
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
    def _get(klass: Type['ConfigRegistration'],
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
    def name(klass: Type['ConfigRegistration'],
             entry: Dict[str, Any]) -> str:
        '''
        Returns the NAME entry of this registration entry.
        '''
        value = klass._get(klass.NAME, entry)
        return value

    @classmethod
    def dotted(klass: Type['ConfigRegistration'],
               entry: Dict[str, Any]) -> label.DotStr:
        '''
        Returns the DOTTED entry of this registration entry.
        '''
        value = klass._get(klass.DOTTED, entry)
        return label.normalize(value)

    @classmethod
    def path_root(klass:  Type['ConfigRegistration'],
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
    def path_run(klass:      Type['ConfigRegistration'],
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
    def path_test(klass: Type['ConfigRegistration'],
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
    def path_ignore_files(klass: Type['ConfigRegistration'],
                          entry: Dict[str, Any]) -> Nullable[str]:
        '''
        Returns the PATH_IGNORE_FILES entry of this registration entry.

        PATH_IGNORE_FILES should be a list of strings and regexes to match
        while checking file names. A matching file will be ignored.
        '''
        return klass._get(klass.PATH_IGNORE_FILES, entry)

    @classmethod
    def path_ignore_dirs(klass: Type['ConfigRegistration'],
                         entry: Dict[str, Any]) -> Nullable[str]:
        '''
        Returns the PATH_IGNORE_DIRS entry of this registration entry.

        PATH_IGNORE_DIRS should be a list of strings and regexes to match while
        checking directory names. A matching dir will be ignored.
        '''
        return klass._get(klass.PATH_IGNORE_DIRS, entry)

    @classmethod
    def force_test(klass: Type['ConfigRegistration'],
                   entry: Dict[str, Any]) -> Nullable[bool]:
        '''
        Returns the FORCE_TEST entry of this registration entry.

        FORCE_TEST, if it exists, should be true to force registration of
        testing classes or false to force skipping test class registration.

        Generally, not supplying is best choice - it will be auto-detected.
        '''
        return klass._get(klass.FORCE_TEST, entry)


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
                    log_dotted:    label.DotStr) -> (bool, label.DotStr):
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
    ignores = (ConfigRegistration.path_ignore_files(entry) or None)
    ignore_dirs = (ConfigRegistration.path_ignore_dirs(entry) or None)
    find_ut = (ConfigRegistration.force_test(entry) or None)

    log.group_multi(_LOG_INIT,
                    log_dotted,
                    "Settings for {} ({}): {}",
                    name, dotted,
                    # TODO v://future/2021-03-14T12:27:54
                    # data={,
                    {
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
                                 log_dotted,
                                 ignores, ignore_dirs,
                                 find_ut)
    registrar_names, registree_names, unknown_names = module_names

    # TODO v://future/2021-03-14T12:27:54
    # add registrar_names, registree_names, unknowns to log as 'data'.
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
    if unknown_names:
        log.group_multi(_LOG_INIT,
                        log_dotted,
                        f"{len(unknown_names)} unknown "
                        f"{text.plural(unknown_names, 'module')} "
                        f"found for {name} ({dotted})! "
                        "Modules did not get ignored but also do not "
                        "match any filenames for registrars/registrees?",
                        log_minimum=log.Level.WARNING)

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

def _import(module: str, log_dotted: label.DotStr) -> ModuleType:
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
# Smart searching?
# -----------------------------------------------------------------------------

# This takes about 0.54 seconds (as of [2021-03-28]) running in a Docker
# container, running in a WSL'd Ubuntu 20.04 instance. Be nice to go faster but
# posix.stat() is taking up 0.47 of those seconds for 411 files/dirs.
def _find_modules(root:          paths.Path,
                  registrars:    List[str]                             = [],
                  registrars_ut: List[str]                             = [],
                  registrees:    List[str]                             = [],
                  registrees_ut: List[str]                             = [],
                  log_dotted:    Optional[label.DotStr]                = None,
                  ignores:       Optional[Set[Union[str, re.Pattern]]] = None,
                  ignore_dirs:   Optional[Set[Union[str, re.Pattern]]] = None,
                  find_ut:       Optional[bool]                        = None,
                  ) -> Tuple[List[str], List[str], List[str]]:
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

    Returns a 3-tuple of lists of strings of module names:
      - Tuple is:
        - Tuple[0]: Registrars found.
        - Tuple[1]: Registrees found.
        - Tuple[2]: Unknowns found.
          - Didn't get ignored but also not registrar/registree files.
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

    ignore_dirs = ignore_dirs or _FIND_MODULE_IGNORES_DIRS
    ignores = ignores or _FIND_MODULE_IGNORES

    base_path = root
    base_name = base_path.name

    # ------------------------------
    # Validate the root.
    # ------------------------------

    if root.exists():
        if root.is_dir():
            log.group_multi(_LOG_INIT,
                            log_dotted,
                            "Find module root is valid.\n"
                            "  base: {}\n"
                            "  path: {}\n"
                            "  find: \n"
                            "    registrars: {}\n"
                            "    registrees: {}",
                            base_name, base_path,
                            import_registrars, import_registrees)
        else:
            log.group_multi(_LOG_INIT,
                            log_dotted,
                            "Find module root is not a directory!\n"
                            "  base: {}\n"
                            "  path: {}\n"
                            "  find: \n"
                            "    registrars: {}\n"
                            "    registrees: {}",
                            base_name, base_path,
                            import_registrars, import_registrees,
                            log_minimum=log.Level.ERROR)
            msg = "Find module root is not a directory!"
            data = {
                'root': root,
                'registrars': registrars,
                'registrars-unit-test': registrars_ut,
                'registrees': registrees,
                'registrees-unit-test': registrees_ut,
                'ignore_dirs': ignore_dirs,
                'ignores': ignores,
                'import_registrars': import_registrars,
                'import_registrees': import_registrees,
                'base_path': base_path,
                'base_name': base_name,
            }
            error = NotADirectoryError(msg, data)
            raise log.exception(error, msg)

    else:
        log.group_multi(_LOG_INIT,
                        log_dotted,
                        "Find module root does not exist!\n"
                        "  base: {}\n"
                        "  path: {}\n"
                        "  find: \n"
                        "    registrars: {}\n"
                        "    registrees: {}",
                        base_name, base_path,
                        import_registrars, import_registrees,
                        log_minimum=log.Level.ERROR)
        msg = "Find module root does not exist!"
        data = {
            'root': root,
            'registrars': registrars,
            'registrars-unit-test': registrars_ut,
            'registrees': registrees,
            'registrees-unit-test': registrees_ut,
            'ignore_dirs': ignore_dirs,
            'ignores': ignores,
            'import_registrars': import_registrars,
            'import_registrees': import_registrees,
            'base_path': base_path,
            'base_name': base_name,
        }
        error = NotADirectoryError(msg, data)
        raise log.exception(error, msg)

    # ------------------------------
    # Find the modules.
    # ------------------------------
    return _scan_tree(log_dotted,
                      base_name,
                      base_path,
                      import_registrars,
                      import_registrees,
                      ignores,
                      ignore_dirs,
                      find_ut)


def submodule(module_relative: paths.Path) -> label.DotStr:
    '''
    The sub-module's name to export should be relative to our start
    path (`module_path`) and without its file extension.
    '''
    return label.from_path(module_relative.with_suffix(''))


def _ignore_dir(log_dotted: label.DotStr,
                path:       paths.PathType,
                ignores:    Set[Union[str, re.Pattern]]) -> bool:
    '''
    Checks if the directory `path_relative` (relative to `path_root`), should
    be ignored or not according to the ignore set and import lists.

    Don't call this for the root - you should not ignore that.
    '''
    # Match type.
    matched_on = None
    # Match from `ignores` - str itself or re.Pattern's pattern string.
    matching = None
    # What matched? dir_name for str; regex search result for re.Pattern.
    matched = None
    # Need only the dir name for a string comparison; also want it for logs.
    dir_name = paths.cast(path).stem

    # Return Value: Should it be ignored or not?
    ignore = False

    # ------------------------------
    # Check list of explicit ignores.
    # ------------------------------
    for check in ignores:
        # Can check strings or regexs, so which one is this?
        if isinstance(check, str):
            # Ignore only if full match.
            if check == dir_name:
                ignore = True
                matched_on = "string"
                matching = check
                matched = dir_name

        elif isinstance(check, re.Pattern):
            # Need a string of full path to do our regex comparisons.
            full_path = str(path)
            # Ignore if regex /does/ matches.
            match = check.search(full_path)
            if match:
                ignore = True
                matched_on = "regex"
                matching = check.pattern
                matched = match.groups()

        # If we've found a reason to ignore this, quit early.
        if ignore:
            break

    # ------------------------------
    # Result?
    # ------------------------------
    if log.will_output(*_LOG_INIT):
        if ignore:
            log.group_multi(_LOG_INIT,
                            log_dotted,
                            "Ignoring Directory:\n"
                            "          path: {}\n"
                            "     directory: {}\n"
                            "   ignore type: {}\n"
                            "  ignore match: {}\n"
                            "    matched on: {}",
                            path,
                            dir_name,
                            matched_on,
                            matching,
                            matched,
                            log_minimum=log.Level.DEBUG)
        else:
            log.group_multi(_LOG_INIT,
                            log_dotted,
                            "Directory To Scan:\n"
                            "         path: {}\n"
                            "    directory: {}\n",
                            path,
                            dir_name,
                            log_minimum=log.Level.DEBUG)
    return ignore


def _ignore(log_dotted:        label.DotStr,
            path_root:         paths.Path,
            path_relative:     paths.Path,
            ignores:           Set[Union[str, re.Pattern]],
            import_registrars: List[str],
            import_registrees: List[str]) -> bool:
    '''
    Checks if the file `path_relative` (relative to `path_root`), should be
    ignored or not according to the ignore set and import lists.
    '''
    ignore = False
    path = path_root / path_relative
    module_name = path.stem
    module_ext = path.suffix

    # ------------------------------
    # Check list of explicit ignores.
    # ------------------------------
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

    # ------------------------------
    # Early out?
    # ------------------------------
    # This path should be ignored, so continue on.
    if ignore:
        log.group_multi(_LOG_INIT,
                        log_dotted,
                        "Ignoring:\n"
                        "          path: {}\n"
                        "        module: {}\n"
                        "   ignore type: {}\n"
                        "  ignore match: {}",
                        path_relative, module_name,
                        matched_on, matching,
                        log_minimum=log.Level.DEBUG)
        return ignore

    # ------------------------------
    # Check for implicit ignoring conditions
    # ------------------------------.
    if (module_name not in import_registrars
            and module_name not in import_registrees):
        ignore = True
        log.group_multi(_LOG_INIT,
                        log_dotted,
                        "Ignoring sub-module to process: {}\n"
                        "    path: {}\n"
                        "  module: {}\n"
                        "  reason: no filename match",
                        submodule(path_relative),
                        path_relative, module_name,
                        log_minimum=log.Level.DEBUG)

    # Import the match only if it's the correct file type.
    elif not path.is_file():
        ignore = True
        log.group_multi(_LOG_INIT,
                        log_dotted,
                        "Ignoring (matching): {}\n"
                        "    path: {}\n"
                        "  module: {}\n"
                        "  reason: Not a file.",
                        submodule(path_relative),
                        path_relative, module_name,
                        log_minimum=log.Level.DEBUG)

    elif module_ext not in ('.py', '.pyw'):
        ignore = True
        log.group_multi(_LOG_INIT,
                        log_dotted,
                        "Ignoring (matching): {}\n"
                        "    path: {}\n"
                        "  module: {}\n"
                        "  reason: Not a python module file extension "
                        "(.py, .pyw).",
                        submodule(path_relative),
                        path_relative, module_name,
                        log_minimum=log.Level.DEBUG)

    # `ignore` should still be False, so this is not needed, but is implied.
    # else:
    #   # ------------------------------
    #   # Failed all ignore conditions - do not ignore.
    #   # ------------------------------
    #   ignore = False

    return ignore


def _sort(log_dotted:        label.DotStr,
          path_root:         paths.Path,
          path_relative:     paths.Path,
          import_registrars: List[str],
          import_registrees: List[str],
          export_registrars: List[str],
          export_registrees: List[str],
          unknowns:          List[str]) -> None:
    '''
    Figures out which of the export/unknown output lists that `path_relative`
    belongs to.

    Given `path_root`, `path_relative`, and the input lists
    (`import_registrars` & `import_registrees`), figure out which output list
    to place it in:
      - `export_registrars`
      - `export_registrees`
      - `unknowns`

    Appends `submodule()` to the correct list; returns None.
    '''
    # filename
    module_name = path_relative.stem
    # path -> DotStr
    submod = submodule(path_relative)

    match = True
    if module_name in import_registrars:
        export_registrars.append(submod)

    elif module_name in import_registrees:
        export_registrees.append(submod)

    else:
        match = False
        unknowns.append(submod)

        if log.will_output(*_LOG_INIT):
            module_ext = path_relative.suffix
            log.group_multi(
                _LOG_INIT,
                log_dotted,
                "Found unknown module: {}\n"
                "    path: {}\n"
                "  module: {}\n"
                "     ext: {}\n"
                "  - Does not match registrar or registree names "
                "but also wasn't ignored?!\n"
                "    + registrars: {}\n"
                "    + registrees: {}",
                path_relative, submod,
                module_name, module_ext,
                import_registrars, import_registrees,
                log_minimum=log.Level.INFO)

    if match and log.will_output(*_LOG_INIT):
        module_ext = path_relative.suffix
        log.group_multi(_LOG_INIT,
                        log_dotted,
                        "Found matching module: {}\n"
                        "    path: {}\n"
                        "  module: {}"
                        + ("\n     ext: {}" if module_ext else ""),
                        path_relative, submodule,
                        module_name, path_relative.suffix,
                        log_minimum=log.Level.INFO)


def _scan(log_dotted: label.DotStr,
          directory:  os.DirEntry,
          ignores:    Set[Union[str, re.Pattern]]) -> Optional[Iterator]:
    '''
    Check path and return either None or an `os.scandir()` iterator.
    '''
    if _ignore_dir(log_dotted, directory.name, ignores):
        return None
    return os.scandir(directory.path)


def _scan_tree(log_dotted:        Optional[label.DotStr],
               root_name:         str,
               root_path:         paths.Path,
               import_registrars: List[str],
               import_registrees: List[str],
               ignore_files:      Set[Union[str, re.Pattern]],
               ignore_dirs:       Set[re.Pattern],
               find_ut:           bool
               ) -> Tuple[List[str], List[str], List[str]]:
    '''
    Find the import modules using os's `scandir()`, which is much faster than
    `pathlib.iterdir()` and `os.walk()`.

    `iterdir()`:
      - Just took too long.
      - Had too many calls to `posix.stat()`.
    `os.walk()` uses `scandir()`, so it had potential... but:
      - No way to stop it from walking all of ".git/", or other 'ignore' dirs.
      - Doesn't return DirEntry, so had to do additional `posix.stat()` to
        figure out file/dir.
    '''
    # Original idea from https://stackoverflow.com/a/5135444/425816
    # But using os.walk, which uses os.scandir, which is much much more
    # performant than my original pathlib.iterdir attempt.
    export_registrars = []
    export_registrees = []
    # Files that somehow got past ignore checks but are also not matching
    # registrar/registree names. /Should/ never happen...
    unknowns = []

    # Get module info from root path.
    log.group_multi(_LOG_INIT,
                    log_dotted,
                    "Finding modules...\n"
                    "  unit-testing?: {}\n"
                    "         module: {}\n"
                    "           path: {}\n"
                    "  find: \n"
                    "     registrars: {}\n"
                    "     registrees: {}",
                    find_ut, root_name, root_path,
                    import_registrars, import_registrees)

    # Start off with the root dir. Append more dir scans as we find valid ones.
    scans = [root_path, ]
    scanned_paths = 0
    # Pull the next directory string off of `scans` and do a scan of it for
    # files/dirs we want.
    for directory in scans:
        with os.scandir(directory) as entries:
            for entry in entries:
                scanned_paths += 1

                # ------------------------------
                # Directories
                # ------------------------------
                if (entry.is_dir()
                        and not _ignore_dir(log_dotted,
                                            entry.path,
                                            ignore_dirs)):
                    # Add to our list of dirs to scan.
                    scans.append(entry.path)
                    continue

                # ------------------------------
                # Files
                # ------------------------------

                # ---
                # Set-up for checking files.
                # ---
                path_relative = paths.cast(entry.path).relative_to(root_path)

                # ---
                # Check each module file.
                # ---
                if _ignore(log_dotted,
                           root_path,
                           path_relative,
                           ignore_files,
                           import_registrars,
                           import_registrees):
                    continue

                # Alright; sort this guy into an import list.
                _sort(log_dotted,
                      root_path,
                      path_relative,
                      import_registrars,
                      import_registrees,
                      export_registrars,
                      export_registrees,
                      unknowns)

    # ---
    # Done; log info and return.
    # ---
    if log.will_output(log.Group.START_UP):
        log.group_multi(_LOG_INIT,
                        log_dotted,
                        "Done scanning for modules.\n"
                        "  scanned: {}\n"
                        "  matches: {}\n",
                        scanned_paths,
                        len(export_registrars) + len(export_registrees))

    if export_registrars and log.will_output(log.Group.START_UP):
        module_log = []
        for module in export_registrars:
            module_log.append("    - " + module)
        log.group_multi(_LOG_INIT,
                        log_dotted,
                        "Done finding registrar modules.\n"
                        "   module: {}\n"
                        "  matches: {}\n"
                        "{}",
                        root_name,
                        len(export_registrars),
                        '\n'.join(module_log))

    if export_registrees and log.will_output(log.Group.START_UP):
        module_log = []
        for module in export_registrees:
            module_log.append("    - " + module)
        log.group_multi(_LOG_INIT,
                        log_dotted,
                        "Done finding registree modules.\n"
                        "   module: {}\n"
                        "  matches: {}\n"
                        "{}",
                        root_name,
                        len(export_registrees),
                        '\n'.join(module_log))

    if unknowns:
        file_log = []
        for file in unknowns:
            file_log.append("    - " + file)
        log.group_multi(_LOG_INIT,
                        log_dotted,
                        "Found unknown but matching files?!\n"
                        "    module: {}\n"
                        "  unknowns: {}\n"
                        "{}",
                        root_name,
                        len(unknowns),
                        '\n'.join(file_log),
                        log_minimum=log.Level.WARNING)

    return (export_registrars, export_registrees, unknowns)


