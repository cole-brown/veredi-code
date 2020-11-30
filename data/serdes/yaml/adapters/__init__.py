# coding: utf-8

'''
Registerees for the YAML registry.

This should include most (all?) of the modules so that only one file needs to
be included elsewhere to bring all Veredi's YAML constructor/representer
registration together.
'''


# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

def import_and_register() -> None:
    '''
    Imports yaml.adapters sub-modules, which should all do what is necessary to
    register the classes/functions/etc with YAML and with our tag/class
    registry.
    '''
    from . import types
    from . import document
    from . import function
    from . import identity

    from .ecs import component
    from .ecs import system
    from .ecs import general
    from .ecs import template

    from .interface.output import event  # noqa


# -----------------------------------------------------------------------------
# Public Symbols
# -----------------------------------------------------------------------------

# __all__ = [
#     # This module:
#     'document',
#     'function',
#     'identity',

#     # 'ecs' submodule:
#     'component',
#     'system',
#     'general',
#     'template',

#     # 'interface' submodule:
#     'event'
# ]
