# coding: utf-8

'''
Context Helpers for unit test data.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional
import pathlib

from veredi.data.config.context import ConfigContext
from veredi.data.config.config  import Configuration


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# General Unit Test Context
# -----------------------------------------------------------------------------

def test(klass_name:  str,
         func_name:   str,
         repo_path:   Optional[pathlib.Path] = None,
         config:     Optional[Configuration] = None
         ) -> ConfigContext:
    '''
    Creates a context for general tests of `test_type`.
    '''
    return ConfigContext(repo_path,
                         'veredi.zest.zontext.test')


def real_config(klass_name: str,
                func_name:  str,
                repo_path:  Optional[pathlib.Path]  = None,
                config:     Optional[Configuration] = None
                ) -> ConfigContext:
    '''
    Creates a context for general tests of `test_type`.

    Prefers optional `repo_path` to use for ConfigContext.
    Will use `config.make_config_context()` if no `repo_path`.
    Will make an 'empty' ConfigContext if neither optional is supplied.
    '''
    if repo_path:
        return ConfigContext(repo_path,
                             'veredi.zest.zontext.real_config.repo_path')
    elif config:
        return config.make_config_context()
