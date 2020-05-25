# coding: utf-8

'''
Base Repository Pattern for load, save, etc. from
various backend implementations (db, file, etc).
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Any, Dict
from abc import ABC, abstractmethod

from io import TextIOBase
import os
import re
import hashlib

from veredi.logger import log
from veredi.data.config.registry import register
from veredi.base.context import VerediContext, DataContext

from .. import exceptions
# from ..codec import json
from ..codec import yaml


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

class BaseRepository(ABC):

    def __init__(self,
                 repo_name: str,
                 context_name: str,
                 context_key: str) -> None:
        '''
        `repo_name` should be short-ish and will be lowercased. It should
        probably be, like, 'file', 'mysql', 'sqlite3' etc...

        `context_name` and `context_key` are used for Event and Error context.
        '''
        self._context = VerediContext(context_name, context_key)
        self._name = repo_name.lower()

    # --------------------------------------------------------------------------
    # Repo Properties/Methods
    # --------------------------------------------------------------------------

    @property
    def name(self) -> str:
        '''
        Should be short-ish and will be lowercased. It should probably be, like,
        'file', 'mysql', 'sqlite3' etc...
        '''
        return self._name

    # --------------------------------------------------------------------------
    # Context Properties/Methods
    # --------------------------------------------------------------------------

    @property
    def context(self):
        '''
        Will be the VerediContext this class.
        '''
        return self._context

    # --------------------------------------------------------------------------
    # Abstract Methods
    # --------------------------------------------------------------------------

    @abstractmethod
    def load(self,
             context: DataContext) -> TextIOBase:
        '''
        Loads data from repository based on `load_id`, `load_type`.

        Returns io stream.
        '''
        raise NotImplementedError
