# coding: utf-8

'''
Template Repository
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

#-----
# Python
#-----
from abc import ABC, abstractmethod

#-----
# File-Based
#-----
import os
import re
import hashlib

#-----
# Our Stuff
#-----
from veredi                           import log
from veredi.data                      import exceptions
# from veredi.data.serdes.json.serdes import JsonSerdes
from veredi.data.serdes.yaml.serdes   import YamlSerdes


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

THIS_DIR = os.path.dirname(os.path.abspath(__file__))


# -----------------------------------------------------------------------------
# Helper
# -----------------------------------------------------------------------------

def default_root():
    '''Returns absolute path to a file given its path rooted from this file's
    directory (that is, it should probably start with 'data').

    Returns None if file does not exist.

    '''
    path = os.path.join(THIS_DIR, 'data')
    if not os.path.exists(THIS_DIR):
        return None

    return path


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

class TemplateRepository(ABC):

    @abstractmethod
    def load_by_name(self, system, entity, template):
        '''Gets (loads) a template from backend data store by:
          - system name
          - entity type name
          - template name
        ...may need more to pin it down..?

        '''
        pass

    def _to_context(self, system, entity, template):
        '''Convert user-related info we have for whatever operation into a
        context object in case an error needs to throw itself off a cliff.

        '''
        context = {
            'system': system,
            'entity': entity,
            'template': template,
            'repository': self.__class__.__name__,
        }
        return context


class TemplateFileTree(TemplateRepository):
    # ---
    # File Names
    # ---
    _TYPE_TEMPLATE = "template"
    _TYPE_REQUIREMENTS = "required"
    _NAME_FMT = "{template:s}.{type:s}.{ext:s}"

    # ---
    # Path Names
    # ---
    _HUMAN_SAFE = re.compile(r'[^\w\d-]')
    _REPLACEMENT = '_'

    def __init__(self, root_of_everything=None,
                 file_sys_safing_fn=None,
                 data_serdes=None):
        if root_of_everything:
            self.root = os.path.abspath(root_of_everything)
        else:
            self.root = default_root()

        # Use system-defined or set to our defaults.
        self._safing_fn = file_sys_safing_fn or self._to_human_readable
        self.data_serdes = data_serdes or YamlSerdes()

    def __str__(self):
        return (
            f"{self.__class__.__name__}: "
            f"ext:{self.data_serdes.name} "
            f"root:{self.root}"
        )

    # --------------------------------------------------------------------------
    # Parent's Abstract Methods
    # --------------------------------------------------------------------------

    def load_by_name(self, system, entity, template):
        '''Gets (loads) a template from backend data store by template name.'''
        path = self._to_path(system, entity)
        filename = self._to_filename(template)
        filepath = os.path.join(path, filename)
        return self._load_file(filepath,
                               self._to_context(system, entity, template))

    # --------------------------------------------------------------------------
    # Path Safing
    # --------------------------------------------------------------------------

    def _safe_path(self, root, *args):
        '''Makes args safe with self._safing_fn, then joins them together
        with root path into a full path string.

        '''
        components = []
        for each in args:
            components.append(self._safing_fn(each))

        return os.path.join(root, *components)

    @staticmethod
    def _to_human_readable(string):
        return TemplateFileTree._HUMAN_SAFE.sub(TemplateFileTree._REPLACEMENT,
                                              string)

    @staticmethod
    def _to_hashed(string):
        return hashlib.sha256(string.encode()).hexdigest()

    # --------------------------------------------------------------------------
    # Helpers
    # --------------------------------------------------------------------------

    def _to_path(self, system, entity):
        '''Convert input to path and filename.'''
        path = self._safe_path(self.root,
                               system, entity)
        return path

    def _to_filename(self, template, is_requirements=False):
        _type = (self._TYPE_REQUIREMENTS
                 if is_requirements else
                 self._TYPE_TEMPLATE)

        return self._NAME_FMT.format(template=template,
                                     type=_type,
                                     ext=self.data_serdes.name)

    def _load_file(self, path, error_context):
        '''Load a single data file from path.

        Raises:
          - exceptions.LoadError
            - wrapped error from self.data_serdes._load()
              - e.g. JSONDecodeError
        '''

        data = None
        with open(path, 'r') as f:
            # Can raise an error - we'll let it.
            try:
                data = self.data_serdes._load(f, error_context)
            except exceptions.LoadError:
                # Let this one bubble up as-is.
                data = None
                raise
            except Exception as e:
                # Complain that we found an exception we don't handle.
                # ...then let it bubble up as-is.
                log.error("Unhandled exception:", e)
                data = None
                raise

        return data
