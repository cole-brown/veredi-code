# coding: utf-8

'''
Entity's Life Cycle System. Manages adding, removing entities to a
scene in a safe manner.

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

from typing import Union, Type, Iterable, Optional, Set, Any

from veredi.logger import log
from veredi.entity.component import (ComponentId,
                                     INVALID_COMPONENT_ID,
                                     Component,
                                     ComponentError,
                                     CompIdOrType)
from veredi.entity.entity import (EntityId,
                                  EntityTypeId,
                                  INVALID_ENTITY_ID,
                                  Entity,
                                  EntityLifeCycle)
from .system import SystemHealth
from .time import TimeManager

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

class EntityManager:
    '''
    Manages the life cycles of entities/components.
    '''

    def __init__(self) -> None:
        '''Initializes this thing.'''
        # TODO: Pools instead of allowing stuff to be allocated/deallocated?

        self._new_entity_id:  EntityId      = INVALID_ENTITY_ID
        self._entity_create:  Set[EntityId] = set()
        self._entity_destroy: Set[EntityId] = set()

        self._entity: Dict[EntityId, 'Entity'] = {}
        # self._entity_type?

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

        Does not care about current life cycle state of entity.
        '''
        return self._entity.get(entity_id, None)

    def create(self,
               type_id: EntityTypeId,
               *args: Any,
               **kwargs: Any) -> EntityId:
        '''
        Creates an entity with the supplied args. This is the start of
        the life cycle of the entity.

        Returns the entity id.

        Entity will be cycled to ALIVE during the LIFE tick.
        '''
        self._new_entity_id += 1

        entity = Entity(self._new_entity_id, type_id, *args, **kwargs)
        self._entity[self._new_entity_id] = entity
        self._entity_create.add(self._new_entity_id)
        entity._life_cycled(EntityLifeCycle.CREATING)

        # TODO Event?

        return self._new_entity_id

    def destroy(self, entity_id: EntityId) -> None:
        '''
        Cycles entity to DEATH now... This is the 'end' of the life cycle
        of the entity.

        Entity will be fully removed from our pools on the DEATH tick.
        '''
        entity = self.get(entity_id)
        if not entity:
            return

        entity._life_cycle = EntityLifeCycle.DESTROYING
        self._entity_destroy.add(entity.id)
        # TODO Event?

    def add(self, entity_id: EntityId, *components: Component) -> None:
        '''
        Add component(s) to an entity.

        This is the end of this as far as EntityManager is concerned -
        ComponentManager will do things for the Component's life cycle if
        necessary.
        '''
        entity = self.get(entity_id)
        if not entity:
            return
        entity._add_all(components)
        # TODO Event?

    def remove(self, entity_id: EntityId, *components: CompIdOrType) -> None:
        '''
        Remove components from an entity.

        `components` can be component objects or types.

        This is the end of this as far as EntityManager is concerned -
        ComponentManager will do things for the Component's life cycle if
        necessary.
        '''
        entity = self.get(entity_id)
        if not entity:
            return
        entity._remove_all(components)
        # TODO Event?

    # --------------------------------------------------------------------------
    # Game Loop: Component/Entity Life Cycle Updates
    # --------------------------------------------------------------------------

    def creation(self,
                 time: TimeManager) -> SystemHealth:
        '''
        Runs before the start of the tick/update loop.

        Updates entities in CREATING state to ALIVE state.
        '''

        for entity_id in self._entity_create:
            # Entity should exist in our pool, otherwise we don't
            # care about it...
            entity = self.get(entity_id)
            if (not entity
                    or entity._life_cycle != EntityLifeCycle.CREATING):
                continue

            try:
                # Bump it to alive now.
                entity._life_cycled(EntityLifeCycle.ALIVE)

            except EntityError as error:
                log.exception(
                    error,
                    "EntityError in creation() for entity_id {}.",
                    entity_id)
                # TODO: put this entity in... jail or something? Delete?

            # TODO EVENT HERE!

        # Done with iteration - clear the adds.
        self._entity_create.clear()

        return SystemHealth.HEALTHY

    def destruction(self,
                    time: TimeManager) -> SystemHealth:
        '''
        Runs after the end of the tick/update loop.

        Removes entities not in ALIVE state from entity pools.
        '''

        # Check all entities in the destroy pool...
        for entity_id in self._entity_destroy:
            # Entity should exist in our pool, otherwise we don't
            # care about it...
            entity = self.get(entity_id)
            if (not entity
                    # INVALID, CREATING, DESTROYING will all be
                    # cycled into death. ALIVE can stay.
                    or entity._life_cycle == EntityLifeCycle.ALIVE):
                continue

            try:
                # Bump it to dead now.
                entity._life_cycled(EntityLifeCycle.DEAD)
                # ...and forget about it.
                self._entity.pop(entity_id, None)

            except EntityError as error:
                log.exception(
                    error,
                    "EntityError in creation() for entity_id {}.",
                    entity_id)
                # TODO: put this entity in... jail or something? Delete?

            # TODO EVENT HERE!

        # Done with iteration - clear the removes.
        self._entity_destroy.clear()

        return SystemHealth.HEALTHY
