# coding: utf-8

'''
An entity is just a grab bag of Components with an EntityId associated to it.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    Optional, Iterable, Set, Any, NewType,
                    Dict, Union, Type, Callable)
from veredi.base.null import Null, Nullable
if TYPE_CHECKING:
    from ..component import ComponentManager

import enum

from veredi              import log
from veredi.base.null    import Null
from veredi.base.context import VerediContext
from .identity           import (ComponentId,
                                 EntityId)
from .component          import (Component,
                                 CompIdOrType)


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

EntityTypeId = NewType('EntityTypeId', int)
INVALID_ENTITY_TYPE_ID = EntityTypeId(0)


GetCompFn = NewType('GetCompFn',
                    Optional[Callable[[ComponentId], Optional[Component]]])


@enum.unique
class EntityLifeCycle(enum.Enum):
    INVALID    = 0
    CREATING   = enum.auto()
    ALIVE      = enum.auto()
    DESTROYING = enum.auto()
    DEAD       = enum.auto()

    def __str__(self):
        return (
            f"{self.__class__.__name__}.{self._name_}"
        )

    def __repr__(self):
        return (
            f"ELC.{self._name_}"
        )


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

class Entity:
    '''
    An Entity tracks its EntityId and life cycle, but primarily holds a
    collection of its Components. The components /are/ the entity,
    basically.
    '''

    def __init__(self,
                 context:           Optional[VerediContext],
                 eid:               EntityId,
                 tid:               EntityTypeId,
                 component_manager: 'ComponentManager') -> None:
        '''DO NOT CALL THIS UNLESS YOUR NAME IS EntityManager!'''
        self._entity_id:         EntityId           = eid
        self._type_id:           EntityTypeId       = tid
        self._life_cycle:        EntityLifeCycle    = EntityLifeCycle.INVALID
        self._component_manager: 'ComponentManager' = component_manager

        # TODO:
        #  - Only hold on to component ids?
        #  - Have getters go ask ComponentManager for component?
        #  - This would make get-by-id O(n) instead of O(1)...
        self._components : Dict[Type[Component], Component] = {}

        self._configure(context)

    def _configure(self, context: Optional[VerediContext]) -> None:
        '''
        Any more set up needed to do to entity based on context.
        '''
        if not context or 'entity' not in context.sub:
            return

        for comp in context.sub['entity'].get('components', ()):
            if isinstance(comp, (ComponentId, Component)):
                self._attach(comp)

    @property
    def id(self) -> EntityId:
        return EntityId.INVALID if self._entity_id is None else self._entity_id

    @property
    def type_id(self) -> EntityTypeId:
        return self._type_id

    @property
    def enabled(self) -> bool:
        return self._life_cycle == EntityLifeCycle.ALIVE

    @property
    def life_cycle(self) -> EntityLifeCycle:
        return self._life_cycle

    def _life_cycled(self, new_state: EntityLifeCycle) -> None:
        '''
        EntityManager calls this to update life cycle. Will be called on:
          - INVALID  -> CREATING   : During EntityManager.create().
          - CREATING -> ALIVE      : During EntityManager.creation()
          - ALIVE    -> DESTROYING : During EntityManager.destroy().
          - DESTROYING -> DEAD     : During EntityManager.destruction()
        '''
        self._life_cycle = new_state

    def comp_or_null(self,
                     component: Component,
                     allow_disabled: bool = False) -> Nullable[Component]:
        '''
        Obeys or ignores `Component.enabled` based on `allow_disabled`.
        Returns component or None.
        '''
        if not component.enabled:
            # Only return disabled component if allowed to.
            return component if allow_disabled else Null()
        return component

    def get(self,
            id_or_type:     CompIdOrType,
            allow_disabled: bool = False) -> Nullable[Component]:
        '''
        Gets a component from this entity by ComponentId or ComponentType. Will
        return the component instance or Null().
        '''
        # Try to get by type first...
        component = self._components.get(id_or_type, None)
        log.debug("Get component '{}' by type: {}",
                  id_or_type, component)
        if component:
            return self.comp_or_null(component, allow_disabled)

        # Ok... id maybe?
        component = self._component_manager.get(id_or_type)
        if component:
            # Make sure it's ours...
            # TODO [2020-06-19]: compare by entity_id instead of getting again
            # and comparing instance id?
            my_comp = self._components.get(type(component), None)
            if my_comp and component == my_comp:
                # If we don't want disabled, and this one isn't enabled
                # (and is therefore disabled), there isn't one for you to
                # have.
                return self.comp_or_null(component, allow_disabled)

        # Fall thorough - ain't got that one.
        return Null()

    def contains(self,
                 comp_set: Set[CompIdOrType]) -> bool:
        '''
        Returns true if this entity is a superset of the desired components.
        I.e. if entity owns all these required ComponentIds/ComponentTypes.
        '''
        # For each component, check that it's in our dictionary.
        return all(self.__contains__(component)
                   for component in comp_set)

    # -------------------------------------------------------------------------
    # EntityManager Interface/Helpers
    # -------------------------------------------------------------------------

    def _attach(self, id_or_comp: Union[ComponentId, Component]):
        '''
        DO NOT CALL THIS UNLESS YOUR NAME IS EntityManager!

        Attaches the component to this entity.
        '''
        component = id_or_comp
        if isinstance(id_or_comp, ComponentId):
            component = self._component_manager.get(id_or_comp)
        if not component:
            log.error("Ignoring 'attach' requested for a non-existing "
                      "component. ID or instance: {} -> {}",
                      id_or_comp, component)
            return

        existing = self._components.get(type(component), None)
        if not existing:
            self._components[type(component)] = component
        else:
            # Entity has component already and it cannot
            # be replaced.
            log.warning(
                "Ignoring 'attach' requested for component type already "
                "existing on entity. entity_id: {}, existing: {}, "
                "requested: {}",
                self.id, existing, component)

    def _attach_all(self,
                    id_or_comp: Iterable[Union[ComponentId, Component]]
                    ) -> None:
        '''
        DO NOT CALL THIS UNLESS YOUR NAME IS EntityManager!

        Tries to _attach() all the supplied components to this entity.
        '''
        for each in id_or_comp:
            self._attach(each)

    def _detach(self, id_or_type: CompIdOrType) -> Optional[Component]:
        '''
        DO NOT CALL THIS UNLESS YOUR NAME IS EntityManager!

        Detaches a component from the entity.
        Returns component if found & detached, else None.

        NOTE: returns component regardless of its `enabled` field.
        '''

        # Type passed in?
        component = self._components.pop(id_or_type, None)
        if component:
            return component

        # Nothing /actually/ to do from now on - we didn't find it in our
        # collection if we reach here, so... can't detach it? We'll mirror
        # get()'s fallback, though, since we're returning the component?
        #
        # Probably not necessary since only EntityManager should call this.

        # Ok... id maybe?
        component = self._component_manager.get(id_or_type)
        if component:
            # Make sure it's ours...
            # TODO [2020-06-19]: compare by entity_id instead of getting again
            # and comparing instance id?
            my_comp = self._components.get(type(component), None)
            if my_comp and component == my_comp:
                # If we don't want disabled, and this one isn't enabled
                # (and is therefore disabled), there isn't one for you to
                # have.
                return component

        return None

    def _detach_all(self, components: Iterable[CompIdOrType]) -> None:
        '''
        DO NOT CALL THIS UNLESS YOUR NAME IS EntityManager!

        Tries to detach() all the supplied components from the entity.
        '''
        for each in components:
            self._detach(each)

    # -------------------------------------------------------------------------
    # Python Interfaces (hashable, ==, 'in')
    # -------------------------------------------------------------------------

    # def __hash__(self):
    #     '''
    #     __hash__ and __eq__ needed for putting in dict, set. We'll make it a
    #     bit easier since EntityId must be unique.
    #     '''
    #     return hash(self._entity_id)

    def __eq__(self, other: Any):
        '''
        Entity == Entity is just an EntityId equality check.
        Otherwise uses python's id() func, the 'is' keyword, or something.
        '''
        if isinstance(other, Entity):
            return self.id == other.id

        return id(self) == id(other)

    def __contains__(self, key: CompIdOrType):
        '''
        This is for any "if component in entity:" sort of check systems
        might want to do.
        '''
        # Don't eval all them args unless it'll be used...
        if log.will_output(log.Level.DEBUG):
            log.debug("{} contains {}? {} -> {}\n    all: {}",
                      self.__class__.__name__,
                      key,
                      self.get(key),
                      bool(self.get(key)),
                      self._components)
        return bool(self.get(key))

    def __str__(self):
        ent_str = (
            f"{self.__class__.__name__}"
            f"[{self.id}, "
            f"type:{self.type_id:03d}, "
            f"{str(self.life_cycle)}]: "
        )
        comps = []
        for each in self._components.values():
            comps.append(str(each))
        comp_str = ', '.join(comps)
        return ent_str + '{' + comp_str + '}'

    def __repr__(self):
        ent_str = (
            f"{self.__class__.__name__}"
            f"[{self.id}, "
            f"type:{self.type_id:03d}, "
            f"{repr(self.life_cycle)}]: "
        )
        comps = []
        for each in self._components.values():
            comps.append(repr(each))
        comp_str = ', '.join(comps)
        return '<v.ent:' + ent_str + '{' + comp_str + '}>'
