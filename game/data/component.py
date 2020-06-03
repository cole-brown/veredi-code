# coding: utf-8

'''
Data component - a component that has persistent data on it.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Union, Any, Iterable, MutableMapping
# import enum
# import re
# import decimal

from veredi.base.context import VerediContext
from veredi.data.config.context import ConfigContext
from veredi.data.exceptions import (DataNotPresentError,
                                    DataRestrictedError)
from ..ecs.base.component   import (Component,
                                    ComponentError)
from ..ecs.base.identity import ComponentId


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

class DataComponent(Component):
    '''
    Component with persistent data.
    '''

    def __init__(self,
                 context: Optional[VerediContext],
                 cid: ComponentId,
                 data: MutableMapping[str, Any] = None) -> None:
        '''DO NOT CALL THIS UNLESS YOUR NAME IS ComponentManager!'''

        # This calls _configure with the context.
        super().__init__(context, cid)

        # Now we'll finish init by setting up our data.
        self._config_data(data)

    def _configure(self,
                   context: Optional[ConfigContext]) -> None:
        '''
        Allows components to grab, from the context/config, anything that
        they need to set up themselves.
        '''
        # ---
        # Context Init Section
        # ---
        # Nothing at the moment.
        pass

    def _config_data(self, data: MutableMapping[str, Any] = None) -> None:

            # All persistent data should go here, or be gathered up in return value
        # of persistent property.
        self._persistent: MutableMapping[str, Any] = data or {}
        # Flag for indicating that this component wants its
        # persistent data saved.
        self._dirty:      bool                     = False

        # ---
        # Data Init Section for subclasses.
        # ---
        self._from_data(data)
        self._verify()

    @property
    def persistent(self):
        return self._persistent

    def _verify(self) -> None:  # §-TODO-§: pass in `requirements`.
        '''
        Verifies our data against a template/requirements data set.

        Raises:
          - DataNotPresentError (VerediError)
          - DataRestrictedError (VerediError)
          - NotImplementedError - temporarily
        '''
        # §-TODO-§ [2020-05-26]: Use component-template, component-requirements
        # here to do the verification?
        raise NotImplementedError

    def _from_data(self, data: MutableMapping[str, Any]):
        '''
        Do any data processing needed for readying this component for use based
        on new data.
        '''
        self._persistent = data

    def _to_data(self):
        '''
        Do any data processing needed for readying this component for
        serialization on new data.
        '''
        return self._persistent
