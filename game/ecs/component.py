# coding: utf-8

'''
Component Manager. Manages life cycle of components, which should generally
follow the life cycle of their entity.

Do not hold onto Entities, Components, etc. They /can/ be destroyed at any time,
leaving you holding a dead object. Only keep the EntityId or ComponentId, then
ask its manager. If the manager returns None, the Entity/Component does not
exist anymore.

Inspired by:
  - Entity Component System design pattern
  - personal pain and suffering
  - mecs: https://github.com/patrick-finke/mecs
  - EntityComponentSystem: https://github.com/tobias-stein/EntityComponentSystem
'''


# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Union, Type, Iterable, Optional, Set, List, Any

from veredi.logger import log
from veredi.entity.component import (ComponentId,
                                     INVALID_COMPONENT_ID,
                                     Component,
                                     ComponentLifeCycle,
                                     ComponentError)
from veredi.entity.entity import (EntityId,
                                  EntityTypeId,
                                  INVALID_ENTITY_ID)
from .system import SystemHealth
from .time import TimeManager

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

class ComponentManager:
    '''
    Manages the life cycles of components.
    '''

    def __init__(self) -> None:
        '''Initializes this thing.'''
        # TODO: Pools instead of allowing stuff to be allocated/deallocated?

        self._new_component_id:  ComponentId      = INVALID_COMPONENT_ID
        self._component_create:  Set[ComponentId] = set()
        self._component_destroy: Set[ComponentId] = set()

        self._component_id:   Dict[ComponentId, Component]           = {}
        self._component_type: Dict[Type[Component], List[Component]] = {}

    def _add(self, id: ComponentId, component: Component) -> None:
        '''
        Insert this component into our pools.
        '''
        self._component_id[id] = component
        type_dict = self._component_type.setdefault(type(component), [])
        type_dict.append(component)

    def _remove(self, id: ComponentId) -> None:
        '''
        Take this component out of our pools.
        '''
        component = self._component_id.pop(id, None)
        if not component:
            return

        type_list = self._component_type.setdefault(type(component), [])
        try:
            type_list.remove(component)
        except ValueError:
            # Don't care if it's already not there.
            pass

    # --------------------------------------------------------------------------
    # API: Component Collection Iteration
    # --------------------------------------------------------------------------

    def each_of_type(self, comp_type: Type[Component]) -> Iterable[Component]:
        '''
        Returns a generator that will return each component of the
        required type.
        '''
        # Look for the specific type, and all parent types.
        for type in comp_type.__class__.__mro__:
            # Walk over all components in that type list...
            for component in self._component_type[type]:
                yield component

    # --------------------------------------------------------------------------
    # API: Component/Component Management
    # --------------------------------------------------------------------------

    def get(self, component_id: ComponentId) -> Optional[Component]:
        '''
        Get component from the component pool and return it. Component's
        LifeCycle is not checked so it might not be alive yet/anymore.
        '''
        return self._component_id.get(component_id, None)

    # TODO: *args: Any? or maybe data: Dict[str, Any]?
    def create(self,
               comp_class: Type[Component],
               *args: Any,
               **kwargs: Any) -> ComponentId:
        '''
        Creates a component with the supplied args. This is the start of
        the life cycle of the component.

        Returns the component id.

        Component will be cycled to ALIVE during the LIFE tick.
        '''
        self._new_component_id += 1
        component = comp_class(self._new_component_id, *args, **kwargs)
        self._add(self._new_component_id, component)
        self._component_create.add(self._new_component_id)
        component._life_cycled(ComponentLifeCycle.CREATING)

        # TODO Event?

        return self._new_component_id

    def destroy(self, component_id: ComponentId) -> None:
        '''
        Cycles component to DEATH now... This is the 'end' of the life cycle
        of the component.

        Component will be fully removed from our pools on the DEATH tick.
        '''
        component = self.get(component_id)
        if not component:
            return

        component._life_cycle = ComponentLifeCycle.DESTROYING
        self._component_destroy.add(component.id)
        # TODO Event?

    # --------------------------------------------------------------------------
    # Game Loop: Component Life Cycle Updates
    # --------------------------------------------------------------------------

    def creation(self,
                 time: TimeManager) -> SystemHealth:
        '''
        Runs before the start of the tick/update loop.

        Updates components in CREATING state to ALIVE state.
        '''

        for component_id in self._component_create:
            # Component should exist in our pool, otherwise we don't
            # care about it...
            component = self.get(component_id)
            if (not component
                    or component._life_cycle != ComponentLifeCycle.CREATING):
                continue

            try:
                # Bump it to alive now.
                component._life_cycled(ComponentLifeCycle.ALIVE)

            except ComponentError as error:
                log.exception(
                    error,
                    "ComponentError in creation() for component_id {}.",
                    component_id)
                # TODO: put this component in... jail or something? Delete?

            # TODO EVENT HERE!

        # Done with iteration - clear the adds.
        self._component_create.clear()

        return SystemHealth.HEALTHY

    def destruction(self,
                    time: TimeManager) -> SystemHealth:
        '''
        Runs after the end of the tick/update loop.

        Removes components not in ALIVE state from component pools.
        '''
        # Check all components in the destroy pool...
        for component_id in self._component_destroy:
            # Component should exist in our pool, otherwise we don't
            # care about it...
            component = self.get(component_id)
            if (not component
                    # INVALID, CREATING, DESTROYING will all be
                    # cycled into death. ALIVE can stay.
                    or component._life_cycle == ComponentLifeCycle.ALIVE):
                continue

            try:
                # Bump it to dead now.
                component._life_cycled(ComponentLifeCycle.DEAD)
                self._remove(component_id)

            except ComponentError as error:
                log.exception(
                    error,
                    "ComponentError in creation() for component_id {}.",
                    component_id)
                # TODO: put this component in... jail or something? Delete?

            # TODO EVENT HERE!

        # Done with iteration - clear the removes.
        self._component_destroy.clear()

        return SystemHealth.HEALTHY
