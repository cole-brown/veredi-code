# coding: utf-8

'''
Helper for unit test data.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Union, Any
import pathlib
import enum


from veredi.logs import log


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

THIS_DIR = pathlib.Path(__file__).resolve().parent
''''veredi/zest/' directory'''

DATA_DIR = THIS_DIR / "zata"
''''veredi/zest/zata' directory - parent for all testing data'''

DATA_UNIT_TEST_DIR = DATA_DIR / "unit"
'''
'veredi/zest/zata/unit' directory - parent for all unit-test level data
'''

DATA_INTEGRATION_DIR = DATA_DIR / "integration"
'''
'veredi/zest/zata/unit' directory - parent for all integration-test level data
'''

DATA_FUNCTIONAL_DIR = DATA_DIR / "functional"
'''
'veredi/zest/zata/unit' directory - parent for all functional-test level data
'''

DEFAULT_CAMPAIGN = 'test-campaign'
'''
Campaign name/game id most of the tests use.
'''

DEFAULT_CONFIG_TEST = pathlib.Path('config.testing.yaml')
'''
Default configuration file for most tests.
'''

DEFAULT_CONFIG_NORMAL = pathlib.Path('config.veredi.yaml')
'''
Default configuration file name for real. Some tests prefer to use it
(e.g. TestType.FUNCTIONAL sometimes).
'''


@enum.unique
class TestType(enum.Enum):
    '''
    Type of testing: Unit, Integration, Functional

    As of [2021-01-25], this link exists for a decent explanation:
    https://www.softwaretestinghelp.com/the-difference-between-unit-integration-and-functional-testing/
    '''

    UNIT        = DATA_UNIT_TEST_DIR
    INTEGRATION = DATA_INTEGRATION_DIR
    FUNCTIONAL  = DATA_FUNCTIONAL_DIR

    def path(self) -> pathlib.Path:
        return self.value


# -----------------------------------------------------------------------------
# Helper
# -----------------------------------------------------------------------------

def retval(path: pathlib.Path) -> Optional[pathlib.Path]:
    '''Returns path if it exists or raises an error if not.'''
    if not path.exists():
        msg = f"Path does not exist: {path}"
        error = FileNotFoundError(msg, path)
        raise log.exception(error, msg)
        return None
    return path


def rooted(test_type: TestType,
           *relative: Union[pathlib.Path, str]) -> Optional[pathlib.Path]:
    '''
    Returns absolute path to a file given its path rooted from our
    testing data directory (for the test_type).

    Returns None if dir/file does not exist.

    Return value is a pathlib.Path if dir/file does exist.
    '''
    return retval(test_type.path().joinpath(*relative))


# -----------------------------------------------------------------------------
# Serdes
# -----------------------------------------------------------------------------

def serdes(test_type: TestType = TestType.UNIT) -> Optional[pathlib.Path]:
    '''
    Returns pathlib.Path to serdes test data.
    '''
    return retval(rooted(test_type, 'serdes'))


# -----------------------------------------------------------------------------
# Repositories
# -----------------------------------------------------------------------------

def repository(test_type: TestType = TestType.UNIT) -> Optional[pathlib.Path]:
    '''
    Returns pathlib.Path to repository test data.
    '''
    return retval(rooted(test_type, 'repository'))


def repository_file_tree(test_type: TestType = TestType.UNIT
                         ) -> Optional[pathlib.Path]:
    '''
    Returns pathlib.Path to FileTreeRepository test data.
    '''
    return retval(rooted(test_type, 'repository', 'file-tree'))


def repository_file_bare(test_type: TestType = TestType.UNIT
                         ) -> Optional[pathlib.Path]:
    '''
    Returns pathlib.Path to FileBareRepository test data.
    '''
    return retval(rooted(test_type, 'repository', 'file-bare'))


# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

def config(filepath: Union[pathlib.Path, str, None],
           test_type: TestType = TestType.UNIT) -> Optional[pathlib.Path]:
    '''
    Returns pathlib.Path to config test data for `test_type`.
    '''
    path = retval(rooted(test_type, 'config'))
    # TODO: group logging for: "if unit_test AND <group> will output..."
    log.debug(f"zpath.config({test_type}): INPUTS: "
              f"filepath: {filepath}, "
              f"path: {path}")
    if not filepath:
        # TODO: group logging for: "if unit_test AND <group> will output..."
        log.debug("zpath.config({test_type}): FINAL VALUES: "
                  f"No filepath; using default path: {path}")
        return path

    path = path / filepath
    # TODO: group logging for: "if unit_test AND <group> will output..."
    log.debug("zpath.config({test_type}): FINAL VALUES: "
              "Adding filepath... returning: "
              f"path: {path} "
              f"retval(): {retval(path)}")
    return retval(path)


def config_id(test_type: TestType, campaign: Any) -> Any:
    '''
    Returns a value for Configuration's `game_id` init param.

    Defaults to DEFAULT_CAMPAIGN.
    '''
    if campaign:
        return campaign
    return DEFAULT_CAMPAIGN


def config_filename(test_type: TestType) -> pathlib.Path:
    '''
    Returns the default config filename to use for the test type.
    '''
    if test_type is TestType.FUNCTIONAL:
        return DEFAULT_CONFIG_NORMAL
    return DEFAULT_CONFIG_TEST
