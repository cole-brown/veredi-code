# coding: utf-8

'''
An entity is just a grab bag of Components with an EntityId associated to it.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Iterable, Set, Any

from .component import EntityId, INVALID_ENTITY_ID, Component
from . import component


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

class Entity:
    '''
    An Entity tracks its EntityId and holds a collection of Components. Nothing
    else. The components /are/ the entity, basically.
    '''

    def __init__(self, eid: EntityId, components: Iterable[Component]) -> None:
        self._entity_id = eid
        self._components = {}
        for each in components:
            self._components[each] = each

    @property
    def id(self) -> EntityId:
        return self._entity_id

    # Disallow setting id.
    # @id.setter
    # def id(self, value: EntityId) -> None:
    #     self._entity_id = value

    def get(self, component: component.InstOrType) -> Optional[Component]:
        '''
        Gets a component type from this entity. Will return the component
        instance or None.
        '''
        return self._components.get(component, None)

    def add(self, component: Component):
        '''
        Adds the component to this entity.
        '''
        existing = self._components.get(component, None)
        if not existing:
            self._components[component] = component

        elif existing.replaceable_with(comp):
            # Entity already has one of these... but it can be replace.
            self._components[component] = component

        else:
            # Entity has component already and it cannot
            # be replaced.
            log.warning(
                "Ignoring 'add' requested for existing component on "
                "existing entity. Existing component refused "
                "replacement. entity_id: {}, existing: {}, new: {}",
                self.id, existing, component)

    def update(self, components: Iterable[Component]) -> None:
        '''
        Tries to add() all the supplied components to this entity.
        '''
        for each in components:
            self.add(each)

    def discard(self, component: Component) -> Optional[Component]:
        '''
        Removes a component from the entity.
        Returns result of component pop() - component or nothing.
        '''
        return self._components.pop(component, None)

    def contains(self, comp_set: Set[Component]) -> bool:
        '''
        Returns true if this entity is a superset of the desired components.
        '''
        return self._components.keys() >= comp_set

    # --------------------------------------------------------------------------
    # Set Interface (hashable, ==, 'in')
    # --------------------------------------------------------------------------

    def __hash__(self):
        return id(self._entity_id)

    def __eq__(self, other: Any):
        '''
        This will make `entity == entity_id` true... So don't do that unless you
        mean to.
        '''
        if isinstance(other, Entity):
            return self.id == other.id

        # Otherwise, try to compare a hash of our components with whatever
        # other's hash is.
        other_hash = None
        if isinstance(other, (set, frozenset)):
            self_hash = Component.hashed(self._components.values())
            other_hash = Component.hashed(other)
            return self_hash == other_hash
        else:
            other_hash = hash(other)

        return hash(self) == other_hash

    def __contains__(self, key):
        return key in self._components

# class EntityMetaData:
#     def __init__(self,
#                  enabled: bool = True,
#                  state: StateLifeCycle = StateLifeCycle.ADDED
#                  ) -> None:
#         self.enabled = enabled
#         self.state = state
