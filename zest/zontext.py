# coding: utf-8

'''
Context Helpers for unit test data.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Union, Any, Dict
import pathlib

from . import zpath, zmake
from veredi.base.context import UnitTestContext
from veredi.data.config.context import ConfigContext
from veredi.data.config.config import Configuration
from veredi.data.config.hierarchy import Document
from veredi.data.repository.base import BaseRepository
from veredi.data.codec.base import BaseCodec


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# ------------------------------------------------------------------------------
# General Unit Test Context
# ------------------------------------------------------------------------------

def test(klass_name:   str,
         func_name:    str,
         repo_path:    Optional[pathlib.Path] = None,
         config:       Optional[Configuration] = None,
         test_type:    Optional[zpath.TestType] = zpath.TestType.UNIT) -> UnitTestContext:
    '''
    Creates a context for general tests of `test_type`.
    '''
    config = config or zmake.config(test_type=test_type,
                                    repo_path=repo_path)
    return config.context


def real_config(klass_name:   str,
                func_name:    str,
                config_path:  Union[str, pathlib.Path] = None,
                repo_path:    Optional[pathlib.Path] = None,
                config:       Optional[Configuration] = None,
                test_type:    Optional[zpath.TestType] = zpath.TestType.UNIT) -> UnitTestContext:
    '''
    Creates a context for general tests of `test_type`.
    '''
    config = config or zmake.config(test_type=test_type,
                                    config_path=config_path,
                                    repo_path=repo_path)
    return config.context


# ------------------------------------------------------------------------------
# Codec Context
# ------------------------------------------------------------------------------

def codec(klass_name:   str,
          func_name:    str,
          test_type:    Optional[zpath.TestType] = zpath.TestType.UNIT) -> UnitTestContext:
    '''
    Creates a context for codec test of `test_type`.
    '''
    path = zpath.codec()
    config = zmake.config()
    context = ConfigContext(path,
                            config)

    # Inject specific codec for unit test.
    config.ut_inject('veredi.codec.yaml',
                     Document.CONFIG,
                     'data',
                     'game',
                     'codec')

    return context


# ------------------------------------------------------------------------------
# Repository Context
# ------------------------------------------------------------------------------

def repo(klass_name:   str,
         func_name:    str,
         config:       Optional[Configuration] = None,
         test_type:    Optional[zpath.TestType] = zpath.TestType.UNIT) -> UnitTestContext:
    '''
    Creates a context for repo test of `test_type`.
    '''
    path = zpath.repository_file_tree(test_type)
    config = config or zmake.config(test_type=test_type,
                                    repo_path=path)
    context = ConfigContext(path,
                            config)

    # Inject specific codec for unit test.
    config.ut_inject('veredi.repository.file-tree',
                     Document.CONFIG,
                     'data',
                     'game',
                     'repository',
                     'type')

    config.ut_inject(str(path),
                     Document.CONFIG,
                     'data',
                     'game',
                     'repository',
                     'directory')

    config.ut_inject('veredi.sanitize.human.path-safe',
                     Document.CONFIG,
                     'data',
                     'game',
                     'repository',
                     'sanitize')

    return context
