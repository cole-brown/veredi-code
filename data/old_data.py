# coding: utf-8

'''
Base class for data-back, data-validate... data.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Any, Union, Iterable
import enum
import re
import decimal

from .exceptions import (DataNotPresentError,
                         DataRestrictedError)


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

class ComponentData:
    _SEPARATORS = r'[_ -]'
    _REPLACEMENT = '_'
    # Valid in game code are:
    #   0 through 9
    #   a through z
    #   A through Z
    #   underscore (_)
    #   period (.)
    #   hyphen (-)
    _REGEX_ALNUMSCORE = re.compile(r'^[a-zA-Z0-9_.-]$')

    @staticmethod
    def make_regex(*args: str) -> str:
        return re.compile(''.join(args))

    def has_regex(regex: re.Pattern, string: str) -> bool:
        return bool(regex.search(string))

    def __init__(self, raw_data) -> None:
        self.raw_data = raw_data


class ComponentTemplate(ComponentData):
    def __init__(self, raw_data) -> None:
        super().__init__(raw_data)


class ComponentRequirement(ComponentData):
    def __init__(self, raw_data) -> None:
        super().__init__(raw_data)
#         raise DataNotPresentError(
#             "Required key '{}' not present in data provided: {}",
#             requirement, self.raw_data)
#         raise DataRestrictedError(
#             "Found restricted key '{}' present in data provided: {}",
#             d_key, kwargs)

    def validate(template: 'ComponentTemplate'):
        for key in self.data:
            pass
