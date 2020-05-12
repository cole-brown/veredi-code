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
from typing import Union, Type, Iterable, Set

# Framework

# Our Stuff
from veredi.logger import log
from veredi.entity import component
from veredi.entity.component import (EntityId,
                                     INVALID_ENTITY_ID,
                                     Component)
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

    def __init__(self):
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


    # # --------------------------------------------------------------------------
    # # Context Manager (aka 'with')
    # # --------------------------------------------------------------------------
    # def __enter__(self):
    #     return self
    #
    # def __exit__(self, type, value, traceback):
    #     self.flush()


    # --------------------------------------------------------------------------
    # API: Entity Collection Iteration
    # --------------------------------------------------------------------------

    def each_with(self, required_components: Set[Type[Component]]) -> Iterable[Set[Component]]:
        '''
        Returns a generator that will return each entity that contains all
        components required.
        '''
        # Walk over all entities...
        for id in self._entity:
            entity = self._entity[id]
            # ...and if this entity has all of the required components,
            # yield it as a value.
            if entity and entity.issuperset(required_components):
                yield entity

    # --------------------------------------------------------------------------
    # API: Component/Entity Management
    # --------------------------------------------------------------------------

    def create(self, *components: Component):
        '''
        Creates an entity with the supplied components. This is the start of the
        life cycle of the entity.

        Returns an entity id. If one or more components are supplied to the
        method, these will be added to the new entity.

        Entity/Components will be added before the start of the next tick.
        '''
        self._new_entity_id += 1
        self._entity_add[self._new_entity_id] = set(components)

        return self._new_entity_id

    def delete(self, entity_id: EntityId):
        '''
        Removes all components from an entity. This is the end of the life cycle
        of the entity.

        Entity/Components will be deleted after the end of the current tick.
        '''
        self._entity_del.add(entity_id)

    def add(self, entity_id: EntityId, *components: Component):
        '''
        Add components to an entity. The entity will be updated with its new
        components at the start of the new tick.
        '''
        entry = self._entity_add.get(entity_id, set())
        entry.update(components)

    def remove(self, entity_id: EntityId, *components: Union[Component, Type[Component]]):
        '''
        Remove components from an entity. The entity will be updated after the
        end of the update tick.

        `components` can be component objects or types.
        '''
        entry = self._entity_rm.get(entity_id, set())
        if entry:
            entry.difference_update(components)

    # --------------------------------------------------------------------------
    # Game Loop: Component/Entity Life Cycle Updates
    # --------------------------------------------------------------------------

    def _transition(self, entity_id, state):
        self._transition[state].add(entity_id)

    def _get_transitions(self, state):
        return self._transition[state]

    def update_life(self, time: float,
                    sys_entities: System, sys_time: System) -> SystemHealth:
        '''
        Runs before the start of the tick/update loop.

        Returns an iterable of entity_ids to run a pre_update on in case they
        need to init any components to entity data.
        '''
        self._run_pre_update.clear()

        for entity_id in self._entity_add:
            # Actual entity
            entity = self._entity.get(entity_id, None)
            # Components to add
            components = self._entity_add[entity_id]

            try:
                # New entity?
                if not entity:
                    # Could be an empty set of components, but that's allowed...
                    # for now. (create() doesn't require components)
                    entity = components
                    self._entity[entity_id] = entity

                # Existing entity, but no new components?
                elif not components:
                    log.error("'Add' requested for existing entity {}, but no "
                              "components supplied for adding: {}",
                              entity_id, components)
                    # TODO: pretty print funcs for:
                    #   entity_id, component, 'entity' (aka bag o' components)

                else:
                    for comp in components:
                        existing = entity.get(comp, None)
                        if not existing:
                            entity.add(comp)
                        elif existing.replaceable_with(comp):
                            # Entity already has one of these... should we replace?
                            entity.discard(existing)
                            entity.add(comp)
                        else:
                            # Entity has component already and it cannot
                            # be replaced.
                            log.warning(
                                "'Add' requested for existing component on "
                                "existing entity. Existing component refused "
                                "replacement. entity: {}, existing: {}, new: {}",
                                entity, existing, comp)
            except exceptions.ComponentError as error:
                log.exception(
                    error,
                    "ComponentError on update_life for entity_id {}.",
                    entity_id)
                # TODO: put this entity in... jail or something?

            if entity:
                self._transition(entity_id, component.StateLifeCycle.ADDED)

        return self._get_transitions(component.StateLifeCycle.ADDED)

    def update_death(self, time: float,
                     sys_entities: System, sys_time: System) -> SystemHealth:
        '''
        Runs after the end of the tick/update loop.

        Returns an iterable of entity_ids to run a post_update on in case
        anything needs updating after a component loss.
        '''
        self._run_post_update.clear()

        # Full delete of entities first... Skips having to delete some
        # components, then deleting whole entity anyways.
        for entity_id in self._entity_del:
            # Actual entity
            entity = self._entity.pop(entity_id, None)
            if entity:
                self._transition(entity_id, component.StateLifeCycle.REMOVED)

        # Delete of select components next.
        for entity_id in self._entity_rm:
            # Actual entity
            entity = self._entity.pop(entity_id, None)
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
                    existing = entity.get(comp, None)
                    if existing:
                        entity.discard(comp)
                        removed = True
                    else:
                        # Entity has component already and it cannot
                        # be replaced.
                        log.warning(
                            "'Removed' requested for non-existent component on "
                            "existing entity. "
                            "entity: {}, existing: {}, rm-request: {}",
                            entity, existing, comp)

            if removed:
                self._transition(entity_id, component.StateLifeCycle.REMOVED)

        return self._get_transitions(component.StateLifeCycle.REMOVED)
