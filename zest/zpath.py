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

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

THIS_DIR = pathlib.Path(__file__).resolve().parent
DATA_DIR = THIS_DIR / "zata"
DATA_UNIT_TEST_DIR = DATA_DIR / "unit"
DATA_INTEGRATION_DIR = DATA_DIR / "integration"
DATA_FUNCTIONAL_DIR = DATA_DIR / "functional"

DEFAULT_CAMPAIGN = 'test-campaign'

@enum.unique
class TestType(enum.Enum):
    UNIT        = DATA_UNIT_TEST_DIR
    INTEGRATION = DATA_INTEGRATION_DIR
    FUNCTIONAL  = DATA_FUNCTIONAL_DIR

    def path(self) -> pathlib.Path:
        return self.value


# -----------------------------------------------------------------------------
# Helper
# -----------------------------------------------------------------------------

def retval(path: pathlib.Path) -> Optional[pathlib.Path]:
    '''Returns path if it exists or None if not.'''
    if not path.exists():
        return None
    return path


def rooted(test_type: TestType,
           *relative: Union[pathlib.Path, str]) -> Optional[pathlib.Path]:
    '''Returns absolute path to a file given its path rooted from our
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


# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

def config(filepath: Union[pathlib.Path, str, None],
           test_type: TestType = TestType.UNIT) -> Optional[pathlib.Path]:
    '''
    Returns pathlib.Path to config test data.
    '''
    path = retval(rooted(test_type, 'config'))
    if not filepath:
        return path
    path = path / filepath
    return retval(path)


def config_id(test_type: TestType, campaign: Any) -> Any:
    '''
    Returns a value for Configuration's `game_id` init param.

    Defaults to DEFAULT_CAMPAIGN.
    '''
    if campaign:
        return campaign
    return DEFAULT_CAMPAIGN
