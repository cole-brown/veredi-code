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

from typing import Union, Type, Iterable, Optional, Set

from veredi.logger import log
from veredi.entity.component import (ComponentId,
                                     INVALID_COMPONENT_ID,
                                     Component,
                                     ComponentError,
                                     CompInstOrType)
from veredi.entity.entity import (EntityId,
                                  EntityTypeId,
                                  INVALID_ENTITY_ID,
                                  Entity)
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

        self._new_entity_id  = INVALID_ENTITY_ID
        self._entity_add     = {}
        self._entity_remove  = {}
        self._entity_destroy = set()

        self._entity         = {}


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

    def create(self, type_id: EntityTypeId, *components: Component) -> EntityId:
        '''
        Creates an entity with the supplied components. This is the start of the
        life cycle of the entity.

        Returns an entity id. If one or more components are supplied to the
        method, these will be added to the new entity.

        Entity/Components will be added before the start of the next tick.
        '''
        self._new_entity_id += 1

        entity = Entity(self._new_entity_id, type_id, *components)
        self._entity_add[self._new_entity_id] = entity

        return self._new_entity_id

    def destroy(self, entity_id: EntityId) -> None:
        '''
        Removes all components from an entity. This is the end of the life cycle
        of the entity.

        Entity/Components will be destroyed after the end of the current tick.
        '''
        self._entity_destroy.add(entity_id)

    def add(self, entity_id: EntityId, *components: Component) -> None:
        '''
        Add components to an entity. The entity will be updated with its new
        components at the start of the new tick.
        '''
        # TODO: Put on pre-existing entity, but set to disabled or something
        # until creation()?
        entity = self._entity_add.setdefault(entity_id, set())
        entity.update(components)

    def remove(self, entity_id: EntityId, *components: CompInstOrType) -> None:
        '''
        Remove components from an entity. The entity will be updated after the
        end of the update tick.

        `components` can be component objects or types.
        '''
        comp_set = self._entity_remove.get(entity_id, None)
        if comp_set:
            comp_set.update(components)
        else:
            comp_set = set(components)

        self._entity_remove[entity_id] = comp_set

    # --------------------------------------------------------------------------
    # Game Loop: Component/Entity Life Cycle Updates
    # --------------------------------------------------------------------------

    def creation(self,
                 time: TimeManager) -> SystemHealth:
        '''
        Runs before the start of the tick/update loop.

        Returns an iterable of entity_ids to run a pre_update on in case they
        need to init any components to entity data.
        '''

        for entity_id in self._entity_add:
            # Pre-existing entity?
            existing = self._entity.get(entity_id, None)
            # New Entity or Components to add.
            adding = self._entity_add[entity_id]

            try:
                # New entity?
                if not existing:
                    if isinstance(adding, Entity):
                        self._entity[entity_id] = adding
                    else:
                        # Ignore, generally. Maybe they died...
                        log.debug("'Add' requested for components {} to "
                                  "entity id {}, but no entity exists.",
                                  adding, entity_id)

                # Existing entity, but no new components?
                elif not adding:
                    log.error("'Add' requested for existing entity {}, but no "
                              "components supplied for adding: {}",
                              entity_id, adding)
                    # TODO: pretty print funcs for:
                    #   entity_id, component, 'entity' (aka bag o' components)

                # Pre-existing entity, and just created one?!
                elif isinstance(adding, Entity):
                    log.error("'Create' requested for pre-existing entity {}. "
                              "Components supplied for creation: {}",
                              entity_id, adding)

                # Existing entity; adding components; ask for the update.
                else:
                    existing.update(adding)

            except ComponentError as error:
                log.exception(
                    error,
                    "ComponentError on update_life for entity_id {}.",
                    entity_id)
                # TODO: put this entity in... jail or something?

            # TODO EVENT HERE!
            # if entity:
            #     self._transition(entity_id, component.StateLifeCycle.ADDED)

        # Done with iteration - clear the adds.
        self._entity_add.clear()

        return SystemHealth.HEALTHY

    def destruction(self,
                    time: TimeManager) -> SystemHealth:
        '''
        Runs after the end of the tick/update loop.

        Returns an iterable of entity_ids to run a post_update on in case
        anything needs updating after a component loss.
        '''

        # Full destroy of entities first... Skips having to destroy some
        # components, then destorying whole entity anyways.
        for entity_id in self._entity_destroy:
            # Actual entity
            entity = self._entity.pop(entity_id, None)
            # TODO EVENT HERE!
            # if entity:
            #     self._transition(entity_id, component.StateLifeCycle.REMOVED)

        # Done with iteration - clear the destroys.
        self._entity_destroy.clear()

        # Destruction of select components next.
        for entity_id in self._entity_remove:
            # Actual entity
            entity = self._entity.get(entity_id, None)
            if not entity:
                # Entity already doesn't exist; ignore
                continue

            # Components to remove
            components = self._entity_remove[entity_id]
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

            # TODO EVENT HERE!
            # if removed:
            #     self._transition(entity_id, component.StateLifeCycle.REMOVED)

        # Done with iteration - clear the removes.
        self._entity_remove.clear()

        return SystemHealth.HEALTHY
