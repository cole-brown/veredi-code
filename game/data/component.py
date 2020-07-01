# coding: utf-8

'''
Data component - a component that has persistent data on it.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    Optional, Union, Any,
                    Collection, Container, MutableMapping)
from veredi.base.null import Null, Nullable
if TYPE_CHECKING:
    from veredi.base.context        import VerediContext
    from veredi.data.config.context import ConfigContext


from veredi.data.exceptions         import DataNotPresentError
from ..ecs.base.component           import Component
from ..ecs.base.identity            import ComponentId

# Data Stuff
from veredi.data.codec.adapter.dict import DataDict
from veredi.base                    import dotted


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
                 context: Optional['VerediContext'],
                 cid: ComponentId,
                 data: MutableMapping[str, Any] = None) -> None:
        '''DO NOT CALL THIS UNLESS YOUR NAME IS ComponentManager!'''

        # This calls _configure with the context.
        super().__init__(context, cid)

        # Now we'll finish init by setting up our data.
        self._config_data(data)

    def _configure(self,
                   context: Optional['ConfigContext']) -> None:
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
        '''
        Configure our data into whatever it needs to be for runtime.
        '''
        # All persistent data should go here, or be gathered up in return value
        # of persistent property.
        self._persistent = None

        # Flag for indicating that this component wants its
        # persistent data saved.
        self._dirty = False

        # ---
        # Data Init Section for subclasses.
        # ---
        # Verify on raw data, then call our init data function?
        self._verify(data)
        self._from_data(data)

    def _verify(self, data) -> None:  # §-TODO-§: pass in `requirements`.
        '''
        Verifies our data against a template/requirements data set.

        Raises:
          - DataNotPresentError (VerediError)
          - DataRestrictedError (VerediError)
          - NotImplementedError - temporarily
        '''
        # §-TODO-§ [2020-05-26]: Use component-template,
        # component-requirements here to do the verification? For now, simpler
        # verify...

        if not data:
            raise DataNotPresentError(
                "No data supplied.",
                None, None)

        for key in self._REQ_KEYS:
            self._verify_key(key, data, self._REQ_KEYS[key])

    def _verify_key(self,
                    key: str,
                    data: Collection[str],
                    sub_keys: Union[Collection[str], MutableMapping[str, str]]
                    ) -> None:
        # Get this one...
        self._verify_exists(key, data)

        # ...then go one deeper.
        sub_data = data[key]
        for each in sub_keys:
            if isinstance(sub_keys, list):
                self._verify_exists(each, sub_data)
            else:
                self._verify_key(each, sub_data, sub_keys.get(each, ()))

    def _verify_exists(self,
                       key: str,
                       container: Container[str]) -> None:
        if key not in container:
            raise DataNotPresentError(
                f"Key '{key}' not found in our data (in {container}).",
                None, None)

    # -------------------------------------------------------------------------
    # Persistent Data
    # -------------------------------------------------------------------------

    @property
    def persistent(self):
        return self._persistent

    def _from_data(self, data: MutableMapping[str, Any]):
        '''
        Do any data processing needed for readying this component for use based
        on new data.
        '''
        self._persistent = DataDict(data)

    def _to_data(self):
        '''
        Do any data processing needed for readying this component for
        serialization on new data.
        '''
        return self._persistent

    # -------------------------------------------------------------------------
    # Generic Data Query API
    # -------------------------------------------------------------------------

    def query(self, *dot_path: str) -> Nullable[Any]:
        '''
        Query this component's data for something on either:
          - a dotted string path.
          - (dotted) string args.
        That is either:
           query('foo.bar')
           query('foo', 'bar')

        E.g. for an ability component with data:
        {
          'ability': {
            'strength': {
              'score': 10,
              'modifier': 'some math string',
            },
            ...
          }
        }

        |------------------------+--------------------|
        | Query                  |             Result |
        |------------------------+--------------------|
        | 'strength.modifier'    | 'some math string' |
        | 'strength.score'       |                 10 |
        | 'strength'             |                 10 |
        | 'strength', 'modifier' | 'some math string' |
        | 'strength', 'score'    |                 10 |
        |------------------------+--------------------|
        '''
        if len(dot_path) == 1:
            # replace, probably, ['strength.score'] with ['strength', 'score']
            dot_path = dotted.split(dot_path[0])

        data = self.persistent
        for each in dot_path:
            data = data.get(each, Null())
        return data
