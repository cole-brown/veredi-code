# coding: utf-8

'''
An entity is just a grab bag of Components with an EntityId associated to it.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Iterable, Set, Any, NewType, Dict, Union, Type

from .component import (ComponentId,
                        INVALID_COMPONENT_ID,
                        Component,
                        CompInstOrType)


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

EntityId = NewType('EntityId', int)
INVALID_ENTITY_ID = EntityId(0)

EntityTypeId = NewType('EntityTypeId', int)
INVALID_ENTITY_TYPE_ID = EntityTypeId(0)


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

class Entity:
    '''
    An Entity tracks its EntityId and holds a collection of Components. Nothing
    else. The components /are/ the entity, basically.
    '''

    def __init__(self,
                 eid: EntityId,
                 tid: EntityTypeId,
                 *components: Component) -> None:
        '''DO NOT CALL THIS UNLESS YOUR NAME IS EntityManager!'''
        self._entity_id = eid
        self._type_id = tid
        self._components = {}
        for comp in components:
            if isinstance(comp, Iterable):
                for each in comp:
                    self._components[type(each)] = each
            else:
                self._components[type(comp)] = comp

    @property
    def id(self) -> EntityId:
        return self._entity_id

    @property
    def type_id(self) -> EntityId:
        return self._type_id

    # Setting ids isn't allowed.

    # TODO: get component by id?

    def get(self, component: CompInstOrType) -> Optional[Component]:
        '''
        Gets a component type from this entity. Will return the component
        instance or None.
        '''
        return self._components.get(component, None)

    # TODO: remove this - put in EntityManager.
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

    # TODO: remove this - put in EntityManager.
    def update(self, components: Iterable[Component]) -> None:
        '''
        Tries to add() all the supplied components to this entity.
        '''
        for each in components:
            self.add(each)

    # TODO: remove this - put in EntityManager.
    def discard(self, component: Component) -> Optional[Component]:
        '''
        Removes a component from the entity.
        Returns result of component pop() - component or nothing.
        '''
        return self._components.pop(component, None)

    def contains(self,
                 comp_set: Set[Union[Type[Component], Component]]) -> bool:
        '''
        Returns true if this entity is a superset of the desired components.
        I.e. if entity.contains({RequiredComp0, RequiredComp2})
        '''
        # For each component, check that it's in our dictionary.
        return all(self.__contains__(component)
                   for component in comp_set)

    # --------------------------------------------------------------------------
    # Python Interfaces (hashable, ==, 'in')
    # --------------------------------------------------------------------------

    # def __hash__(self):
    #     '''
    #     __hash__ and __eq__ needed for putting in dict, set. We'll make it a
    #     bit easier since EntityId must be unique.
    #     '''
    #     return hash(self._entity_id)

    def __eq__(self, other: Any):
        '''
        Entity == Entity is just an id equality check. Otherwise uses id() func.
        '''
        if isinstance(other, Entity):
            return self.id == other.id

        return id(self) == id(other)

    def __contains__(self, key):
        '''
        This is for the any "if component in entity:" sort of check systems
        might want to do.
        '''
        # Convert to type if component instance, otherwise check directly.
        if isinstance(key, Component):
            return type(key) in self._components
        return key in self._components

# class EntityMetaData:
#     def __init__(self,
#                  enabled: bool = True,
#                  state: StateLifeCycle = StateLifeCycle.ADDED
#                  ) -> None:
#         self.enabled = enabled
#         self.state = state
