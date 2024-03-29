# coding: utf-8

'''
Context Helpers for unit test data.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import TYPE_CHECKING, Optional, Type, Dict
if TYPE_CHECKING:
    import unittest

import pathlib

from veredi.data.config.context import ConfigContext
from veredi.data.config.config  import Configuration
from veredi.base.context        import VerediContext, UnitTestContext


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def _metadata(file_name: str,
              test_case: 'unittest.TestCase',
              func_name: str) -> Dict[str, str]:
    '''
    Returns unit testing metadata dict built from inputs.
    '''
    return {
        'file': file_name,
        'suite': test_case.__class__.__name__ if test_case else str(test_case),
        'test': func_name,
    }


# -----------------------------------------------------------------------------
# General Unit Test Context
# -----------------------------------------------------------------------------

def empty(test_case:    'unittest.TestCase',
          func_name:    str,
          context_type: Type[VerediContext],
          ) -> VerediContext:
    '''
     Creates and returns an empty `context_type` context.

    For a UnitTestContext:
      - `file_name` should be __file__ in the caller.
      - `test` and `func_name` should be the caller as well - they are
        supplied to UnitTestContext's constructor if that `context_type` is
        used.

    For other types, `file_name`, `test`, and `func_name` are ignored.

    NOTE: Doesn't to place file/test/func into 'meta' key like `test()` and
    `real_config()` do!
    '''
    if context_type == UnitTestContext:
        return context_type(test_case,
                            func_name,
                            data={})
    return context_type()


def test(file_name:   str,
         test_case:   'unittest.TestCase',
         func_name:   str,
         repo_path:   Optional[pathlib.Path] = None,
         config:      Optional[Configuration] = None
         ) -> ConfigContext:
    '''
    Creates a ConfigContext with 'test' key holding:
      - `file_name`
      - `test_case`
      - `func_name`
    '''
    ctx = ConfigContext(repo_path,
                        'veredi.zest.zontext.test')
    ctx['test'] = _metadata(file_name, test_case, func_name)
    return ctx


def real_config(file_name:  str,
                test_case:  'unittest.TestCase',
                func_name:  str,
                repo_path:  Optional[pathlib.Path]  = None,
                config:     Optional[Configuration] = None
                ) -> ConfigContext:
    '''
    Creates a context for general tests of `test_type`.

    Prefers optional `repo_path` to use for ConfigContext.
    Will use `config.make_config_context()` if no `repo_path`.
    Will make an 'empty' ConfigContext if neither optional is supplied.

    - `file_name` should be __file__ in the caller.
    - `test_case` and `func_name` should be the caller as well - they are
      supplied to UnitTestContext's constructor if that `context_type` is
      used.
    '''
    # Choose which context to make.
    if repo_path:
        ctx = ConfigContext(repo_path,
                            'veredi.zest.zontext.real_config.repo_path')
    elif config:
        ctx = config.make_config_context()
    else:
        ctx = empty(test_case, func_name, ConfigContext)

    # Slip in the testing metadata befor returning.
    ctx['test'] = _metadata(file_name, test_case, func_name)
    return ctx
