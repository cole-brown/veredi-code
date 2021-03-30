# coding: utf-8

'''
Registry for Configuration.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    Optional, Any, Type, Iterable, Dict, List)
if TYPE_CHECKING:
    from veredi.data.config.context import ConfigContext


from veredi.logs           import log
from veredi.data           import background
from veredi.base.context   import VerediContext
from veredi.base.registrar import DecoratorRegistrar, RegisterType
from veredi.base.strings   import label

from ..exceptions          import RegistryError


# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = [
    # ------------------------------
    # File-Local
    # ------------------------------

    # ---
    # Classes
    # ---
    'ConfigRegistry',
]


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Configuration Registry
# -----------------------------------------------------------------------------

class ConfigRegistry(DecoratorRegistrar):
    '''
    Registry for all the registree types that want to be created by
    Configuration and/or referencable in the config files.

    ConfigRegistry mainly gets its registrees via __registry__ files
    using `register()` and `ignore()`, but you can also use the decorator

    ConfigRegistry can also be used as a decorator registry, _BUT_ using it
    this way will only register the decorated class _if/when_ it gets imported!
      e.g.:
        from veredi.data.config.registry import registry
        @registry.register('veredi.jeff.system')
    '''

    # -------------------------------------------------------------------------
    # Dotted Name
    # -------------------------------------------------------------------------

    @classmethod
    def dotted(klass: 'ConfigRegistry') -> str:
        '''
        Returns this registrar's dotted name.
        '''
        return 'veredi.data.config.registry'

    @classmethod
    def name(klass: 'ConfigRegistry') -> str:
        '''
        Returns a short name for this registrar.
        '''
        return 'config.registry'

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def _init_register(self,
                       registree: Type[Any],
                       reg_args:  Iterable[str]) -> bool:
        '''
        This is called before anything happens in `register()`.

        Raise an error if a registration should not be allowed.
        '''
        # TODO: Do we have any checks to do here?
        return True

    # -------------------------------------------------------------------------
    # Registration
    # -------------------------------------------------------------------------

    def _register(self,
                  registree:  Type[Any],
                  reg_label:    Iterable[str],
                  # final key in `reg_args`
                  leaf_key:   str,
                  # A sub-tree of our registration dict, at the correct node
                  # for registering this registree.
                  reg_ours:   Dict,
                  # A sub-tree of the background registration dict, at the
                  # correct node for registering this registree.
                  reg_bg:     Dict) -> None:
        '''
        We want to register to the background with:
          { leaf_key: Any.type_field() }

        `reg_args` is the Iterable of args passed into `register()`.
        `reg_ours` is the place in our registry we placed this registration.
        `reg_bg` is the place in the background we placed this registration.
        '''
        # Get it's type field name.
        try:
            name = registree.type_field()
        except NotImplementedError as error:
            msg = (f"{self.__class__.__name__}._register: '{type(registree)}' "
                   f"(\"{label.regularize(*reg_label)}\") needs to "
                   "implement type_field() function.")
            self._log_exception(error, msg)
            # Let error through. Just want more info.
            raise

        # Set as registered cls/func.
        reg_ours[leaf_key] = registree

        # Save to the background as a thing that has been registered at this
        # level.
        bg_list = reg_bg.setdefault('.', [])
        bg_list.append({leaf_key: name})

    # -------------------------------------------------------------------------
    # Accessors
    # -------------------------------------------------------------------------

    def get(self,
            dotted:   label.LabelInput,
            context:  Optional[VerediContext],
            reg_fallback: Optional[RegisterType] = None
            ) -> Optional[RegisterType]:
        '''
        Get the registree class/function for this `dotted` label.

        If nothing found, raises KeyError unless `reg_fallback` was provided.
        In that case, returns `reg_fallback`.

        If the thing found at `dotted` is not a registree raises a
        RegistryError (e.g. asked for "veredi.data", which is a branch in the
        registree dotted tree: 'veredi.data.codec', 'veredi.data.repository',
        etc...).

        Context just used for errors/exceptions.

        `args` and `kwargs` are passed to the registree for initialization.
        '''
        dotted = label.normalize(dotted)
        self._log_debug("ConfigRegistry.get: "
                        "dotted: {}{}",
                        dotted,
                        (f", fallback: {reg_fallback}"
                         if reg_fallback else
                         ""))

        try:
            registree = self.get_by_dotted(dotted, context)

        except (KeyError, RegistryError):
            # If we have a fallback, return it. Otherwise let the error bubble
            # up.
            if reg_fallback:
                self._log_debug("ConfigRegistry.get: "
                                "No registree for dotted: '{}'. Using "
                                "supplied fallback: {}",
                                dotted,
                                reg_fallback)
                return reg_fallback
            raise

        return registree
