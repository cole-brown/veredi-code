# coding: utf-8

'''
Entity's/Components' Life Cycle System. Manages adding, removing entities to a
scene in an update-loop-safe manner.

"Update-safe" means:
  - Adding happens before the beginning of the normal update loop.
  - Removing happens after the end of the normal update loop.

This way any iteration underway will not be interrupted by the entity that
needed managed.

Inspired by:
  - Entity Component System design pattern
  - personal pain and suffering
  - mecs: https://github.com/patrick-finke/mecs
'''


# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

# Python
from typing import Union, Type, Iterable, Optional, Set
from collections.abc import Iterable as iter_inst

# Framework

# Our Stuff
from veredi.logger import log
from veredi.entity import component
from veredi.entity.component import (EntityId,
                                     INVALID_ENTITY_ID,
                                     Component,
                                     ComponentError)
from veredi.entity.entity import Entity
from . import system

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

class SystemLifeCycle(system.System):
    '''
    Manages the life cycles of entities/components.
    '''

    def __init__(self) -> None:
        '''Initializes this thing.'''
        self._new_entity_id = INVALID_ENTITY_ID
        self._entity_add    = {}
        self._entity_rm     = {}
        self._entity_del    = set()
        self._entity        = {}

        self._entity_transitioned = {
            component.StateLifeCycle.ADDED:   set(),
            component.StateLifeCycle.REMOVED: set(),
        }


    # --------------------------------------------------------------------------
    # API: Entity Collection Iteration
    # --------------------------------------------------------------------------

    def each_with(self, required_components: Set[Type[Component]]) -> Iterable[Entity]:
        '''
        Returns a generator that will return each entity that contains all
        components required.
        '''
        # Walk over all entities...
        for id in self._entity:
            entity = self._entity[id]
            # ...and if this entity has all of the required components,
            # yield it as a value.
            if entity and entity.contains(required_components):
                yield entity

    # --------------------------------------------------------------------------
    # API: Component/Entity Management
    # --------------------------------------------------------------------------

    def get(self, entity_id: EntityId) -> Optional[Entity]:
        '''
        Get an existing/alive entity from the entity pool and return it.

        Does not look for pre-alive entities that are waiting to be born.
        '''
        return self._entity.get(entity_id, None)

    def create(self, *components: Component) -> EntityId:
        '''
        Creates an entity with the supplied components. This is the start of the
        life cycle of the entity.

        Returns an entity id. If one or more components are supplied to the
        method, these will be added to the new entity.

        Entity/Components will be added before the start of the next tick.
        '''
        self._new_entity_id += 1

        adding = set()
        for comp in components:
            if isinstance(comp, set):
                adding.update(comp)
            elif isinstance(comp, iter_inst):
                adding.update(comp)
            else:
                adding.add(comp)

        self._entity_add[self._new_entity_id] = adding

        return self._new_entity_id

    def delete(self, entity_id: EntityId) -> None:
        '''
        Removes all components from an entity. This is the end of the life cycle
        of the entity.

        Entity/Components will be deleted after the end of the current tick.
        '''
        self._entity_del.add(entity_id)

    def add(self, entity_id: EntityId, *components: Component) -> None:
        '''
        Add components to an entity. The entity will be updated with its new
        components at the start of the new tick.
        '''
        entity = self._entity_add.setdefault(entity_id, set())
        entity.update(components)

    def remove(self, entity_id: EntityId, *components: component.InstOrType) -> None:
        '''
        Remove components from an entity. The entity will be updated after the
        end of the update tick.

        `components` can be component objects or types.
        '''
        comp_set = self._entity_rm.get(entity_id, None)
        if comp_set:
            comp_set.update(components)
        else:
            comp_set = set(components)

        self._entity_rm[entity_id] = comp_set

    # --------------------------------------------------------------------------
    # Game Loop: Component/Entity Life Cycle Updates
    # --------------------------------------------------------------------------

    def _transition(self, entity_id: EntityId, state: component.StateLifeCycle) -> None:
        self._entity_transitioned[state].add(entity_id)

    def _get_transitions(self, state: component.StateLifeCycle) -> set:
        return self._entity_transitioned[state]

    def update_life(self,
                    time: float,
                    sys_entities: system.System,
                    sys_time: system.System) -> system.SystemHealth:
        '''
        Runs before the start of the tick/update loop.

        Returns an iterable of entity_ids to run a pre_update on in case they
        need to init any components to entity data.
        '''

        for entity_id in self._entity_add:
            # Actual entity?
            entity = self._entity.get(entity_id, None)
            # Components to add
            components = self._entity_add[entity_id]

            try:
                # New entity?
                if not entity:
                    # Could be an empty set of components, but that's allowed...
                    # for now. (create() doesn't require components)
                    entity = Entity(entity_id, components)
                    self._entity[entity_id] = entity

                # Existing entity, but no new components?
                elif not components:
                    log.error("'Add' requested for existing entity {}, but no "
                              "components supplied for adding: {}",
                              entity_id, components)
                    # TODO: pretty print funcs for:
                    #   entity_id, component, 'entity' (aka bag o' components)

                # Existing entity; have components; ask for update.
                else:
                    entity.update(components)

            except ComponentError as error:
                log.exception(
                    error,
                    "ComponentError on update_life for entity_id {}.",
                    entity_id)
                # TODO: put this entity in... jail or something?

            if entity:
                self._transition(entity_id, component.StateLifeCycle.ADDED)

        # Done with iteration - clear the adds.
        self._entity_add.clear()

        # return self._get_transitions(component.StateLifeCycle.ADDED)
        return system.SystemHealth.HEALTHY

    def update_death(self,
                     time: float,
                     sys_entities: system.System,
                     sys_time: system.System) -> system.SystemHealth:
        '''
        Runs after the end of the tick/update loop.

        Returns an iterable of entity_ids to run a post_update on in case
        anything needs updating after a component loss.
        '''

        # Full delete of entities first... Skips having to delete some
        # components, then deleting whole entity anyways.
        for entity_id in self._entity_del:
            # Actual entity
            entity = self._entity.pop(entity_id, None)
            if entity:
                self._transition(entity_id, component.StateLifeCycle.REMOVED)

        # Done with iteration - clear the deletes.
        self._entity_del.clear()

        # Delete of select components next.
        for entity_id in self._entity_rm:
            # Actual entity
            entity = self._entity.get(entity_id, None)
            if not entity:
                # Entity already doesn't exist; ignore
                continue

            # Components to remove
            components = self._entity_rm[entity_id]
            removed = False

            # Existing entity, but no new components?
            if not components:
                log.error("'Remove' requested for existing entity {}, but no "
                          "components supplied for removing: {}",
                          entity_id, components)
                # TODO: posttty print funcs for:
                #   entity_id, component, 'entity' (aka bag o' components)

            else:
                for comp in components:
                    removed = removed or bool(entity.discard(comp))

            if removed:
                self._transition(entity_id, component.StateLifeCycle.REMOVED)

        # Done with iteration - clear the removes.
        self._entity_rm.clear()

        # return self._get_transitions(component.StateLifeCycle.REMOVED)
        return system.SystemHealth.HEALTHY
