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


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# General Unit Test Context
# -----------------------------------------------------------------------------

def test(klass_name:   str,
         func_name:    str,
         repo_path:    Optional[pathlib.Path] = None
         ) -> ConfigContext:
    '''
    Creates a context for general tests of `test_type`.
    '''
    return ConfigContext(repo_path)


def real_config(klass_name:  str,
                func_name:   str,
                repo_path:   Optional[pathlib.Path] = None
                ) -> ConfigContext:
    '''
    Creates a context for general tests of `test_type`.
    '''
    return ConfigContext(repo_path)
