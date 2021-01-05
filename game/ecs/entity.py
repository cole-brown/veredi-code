# coding: utf-8

'''
Entity's Life Cycle System. Manages adding, removing entities to a
scene in a safe manner.

Do not hold onto Entities, Components, etc. They /can/ be destroyed at any
time, leaving you holding a dead object. Only keep the EntityId or ComponentId,
then ask its manager. If the manager returns None, the Entity/Component does
not exist anymore.

Inspired by:
  - Entity Component System design pattern
  - personal pain and suffering
  - mecs:
    https://github.com/patrick-finke/mecs
  - EntityComponentSystem:
    https://github.com/tobias-stein/EntityComponentSystem
'''


# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    Optional, Union, Type, NewType, Iterable, Set, Dict)
from veredi.base.null import NullNoneOr, Nullable, Null
if TYPE_CHECKING:
    from .time import TimeManager
    from veredi.base.identity import MonotonicIdGenerator

import enum

from veredi.logger             import log
from veredi.base.const         import VerediHealth
from veredi.base.context       import VerediContext
from veredi.data               import background
from veredi.data.config.config import Configuration
from veredi.debug.const        import DebugFlag

from .base.exceptions          import EcsEntityError
from .base.identity            import ComponentId, EntityId
from .base.component           import (Component,
                                       CompIdOrType)
from .base.entity              import (EntityTypeId,
                                       Entity,
                                       EntityLifeCycle)
from .event                    import EcsManagerWithEvents, EventManager, Event
from .component                import ComponentManager


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

@enum.unique
class EntityEventType(enum.Enum):
    COMPONENT_ATTACH = enum.auto()
    COMPONENT_DETACH = enum.auto()


EntityOrNull = NewType('EntityOrNull', Union[Entity, Null])


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

class EntityEvent(Event):
    ...


class EntityLifeEvent(Event):
    pass


class EntityManager(EcsManagerWithEvents):
    '''
    Manages the life cycles of entities/components.

    Uses the Null Pattern object (veredi.base.null.Null) for
    entities/components it doesn't have so you can safely code, say:
        for jeff_ent in all_jeff_entities:
            name = jeff_ent.get(NameComponent).name or fallback_value
            result = jeff_ent.get(ComplicatedComp).do_a_complicated_thing()
            if not result.success:
                self._log_info(...)
            ...

    The entities and components should be either: real or Null(), and so you'll
    get either real returns or Null(). So no need to do all this:
        for jeff_ent in all_jeff_entities:
            if not jeff_ent:
                continue
            name_comp = jeff_ent.get(NameComponent)
            if name_comp:
                name = name_comp.name
            else:
                name = fallback_value
            comp_comp = jeff_ent.get(ComplicatedComp)
            if comp_comp:
                result = comp_comp.do_a_complicated_thing()
                if not result or not result.success:
                    self._log_info(...)
                else:
                    ...
            else:
                ...
            ...
    '''

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def _define_vars(self) -> None:
        super()._define_vars()

        self._component_manager: ComponentManager       = None
        '''
        Handle to the ComponentManager so we can do common things for entities
        like attach a component, check for components, etc.
        '''

        self._entity_id:         'MonotonicIdGenerator' = EntityId.generator()
        '''
        EntityId generator for entity creation.

        This is the definitive place for EntityIds and they should only be
        created from this generator.
        '''

        self._entity_create:     Set[EntityId]          = set()
        '''Entities that will be created soon.'''

        self._entity_destroy:    Set[EntityId]          = set()
        '''Systems that will be destroyed soon.'''

        # TODO: Pool instead of allowing stuff to be allocated/deallocated?
        self._entity:            Dict[EntityId, Entity] = {}
        '''Collection of all Entities. Indexed by ID.'''

    def __init__(self,
                 config:            Optional[Configuration],
                 event_manager:     Optional[EventManager],
                 component_manager: ComponentManager,
                 debug_flags:       NullNoneOr[DebugFlag]) -> None:
        super().__init__(event_manager, debug_flags)

        self._config            = config
        self._component_manager = component_manager

    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------

    @classmethod
    def dotted(klass: 'EntityManager') -> str:
        '''
        The dotted name this Manager has.
        '''
        return 'veredi.game.ecs.manager.entity'

    def get_background(self):
        '''
        Data for the Veredi Background context.
        '''
        return {
            background.Name.DOTTED.key: self.dotted(),
        }

    # -------------------------------------------------------------------------
    # Internal Functions
    # -------------------------------------------------------------------------

    def _cycle_apocalypse(self) -> VerediHealth:
        '''
        Game is ending gracefully. Make sure to murder everyone.
        '''
        # Mark every ent for destruction, then run destruction.
        for eid in self._entity:
            self.destroy(eid)
        health = self.destruction(None)

        health = health.update(
            super()._cycle_apocalypse())

        self.health = health
        return health

    # -------------------------------------------------------------------------
    # API: Entity Collection Iteration
    # -------------------------------------------------------------------------

    def each_with(self,
                  required_component: Type[Component]
                  ) -> Iterable[Entity]:
        '''
        Returns a generator that will return each entity that contains the
        the required component.
        '''
        # Walk over all entities...
        for id in self._entity:
            entity = self._entity[id]
            # ...and if this entity has the required component,
            # yield it as a value.
            if (entity
                    and entity.enabled
                    and required_component in entity):
                yield entity

    def each_with_all(self,
                      required_components: Set[Type[Component]]
                      ) -> Iterable[Entity]:
        '''
        Returns a generator that will return each entity that contains all of
        the components required.
        '''
        # Walk over all entities...
        for id in self._entity:
            entity = self._entity[id]
            # ...and if this entity has all of the required components,
            # yield it as a value.
            if (entity
                    and entity.enabled
                    and entity.contains(required_components)):
                yield entity

    def each_with_any(self,
                      required_components: Set[Type[Component]]
                      ) -> Iterable[Entity]:
        '''
        Returns a generator that will return each entity that contains any of
        the components required.
        '''
        # Walk over all entities...
        for id in self._entity:
            entity = self._entity[id]
            # ...and if this entity has any one of the required components,
            # yield it as a value.
            if (entity and entity.enabled):
                for component in required_components:
                    if component in entity:
                        yield entity

    # -------------------------------------------------------------------------
    # API: Component/Entity Management
    # -------------------------------------------------------------------------

    def get(self, entity_id: EntityId) -> Optional[Entity]:
        '''
        USES Null PATTERN!!!

        Get an existing/alive entity from the entity pool and return it.

        Does not care about current life cycle state of entity.

        Returns the Component object or the Null() singleton object.
        '''
        return self._entity.get(entity_id, Null())

    def get_with_log(self,
                     caller: str,
                     entity_id: 'EntityId',
                     event:     NullNoneOr['Event']         = None,
                     context:   NullNoneOr['VerediContext'] = None,
                     preface:   Optional[str]               = None,
                     ) -> Nullable['Entity']:
        '''
        Calls `get(entity_id)` to get entity. Just returns the entity if it
        exists.

        If it does not exist:
          - Logs at INFO level:
            caller  (e.g. 'IdentityManager.event_identity_req')
            + preface (or "Dropping event {event} - "
                       if preface is None and event is not None)
            + "No entity for its id: {entity_id}"

          - `context` gets logged too - if not None. `context` will be pulled
            from `event` if `event` exists and `context` is not set.

          - returns Null()
        '''
        entity = self.get(entity_id)
        if not entity:
            # Entity disappeared, and that's ok.
            preface = preface or ''
            if event:
                preface = preface or f"Dropping event {event} - "
                if not context:
                    context = event.context
            # Entity disappeared, and that's ok.
            self._log_info("{}: {}No entity for its id: {}",
                           caller, preface, entity_id,
                           context=context)
            return Null()

        return entity

    def create(self,
               type_id: EntityTypeId,
               context: Optional[VerediContext]) -> EntityId:
        '''
        Creates an entity with the supplied args. This is the start of
        the life cycle of the entity.

        Returns the entity id.

        Entity will be cycled to ALIVE during the CREATION tick.
        '''
        eid = self._entity_id.next()

        entity = Entity(context, eid, type_id, self._component_manager)
        if not entity:
            raise self._log_exception(
                EcsEntityError,
                "Failed to create Entity for would-be "
                "entity_id {}. got: {}, context: {}",
                eid, entity, context
            )

        self._entity[eid] = entity
        self._entity_create.add(eid)
        entity._life_cycled(EntityLifeCycle.CREATING)

        self._event_create(EntityLifeEvent,
                           eid,
                           EntityLifeCycle.CREATING,
                           None, False)

        return eid

    def destroy(self, entity_id: EntityId) -> None:
        '''
        Cycles entity to DESTROYING now... This is the 'end' of the life cycle
        of the entity.

        Entity will be fully removed from our pools on the DESTRUCTION tick.
        '''
        entity = self.get(entity_id)
        if not entity:
            return

        entity._life_cycle = EntityLifeCycle.DESTROYING
        self._entity_destroy.add(entity.id)

        self._event_create(EntityLifeEvent,
                           entity_id,
                           EntityLifeCycle.DESTROYING,
                           None, False)

    def attach(self,
               entity_id: EntityId,
               *id_or_comp: Union[ComponentId, Component]) -> None:
        '''
        Add component(s) to an entity.

        This is the end of this as far as EntityManager is concerned -
        ComponentManager will do things for the Component's life cycle if
        necessary.
        '''
        entity = self.get(entity_id)
        if not entity:
            return
        entity._attach_all(id_or_comp)

        self._event_create(EntityEvent,
                           entity_id,
                           EntityEventType.COMPONENT_ATTACH,
                           None, False)

    def detach(self, entity_id: EntityId, *components: CompIdOrType) -> None:
        '''
        Removes components from an entity.

        `components` can be component objects or types.

        This is the end of this as far as EntityManager is concerned -
        ComponentManager will do things for the Component's life cycle if
        necessary.
        '''
        entity = self.get(entity_id)
        if not entity:
            return
        entity._detach_all(components)

        self._event_create(EntityEvent,
                           entity_id,
                           EntityEventType.COMPONENT_DETACH,
                           None, False)

    # -------------------------------------------------------------------------
    # Game Loop: Component/Entity Life Cycle Updates
    # -------------------------------------------------------------------------

    def creation(self,
                 time: 'TimeManager') -> VerediHealth:
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

            except EcsEntityError as error:
                self._log_exception(
                    error,
                    "EcsEntityError in creation() for entity_id {}.",
                    entity_id)
                # TODO: put this entity in... jail or something? Delete?

            self._event_create(EntityLifeEvent,
                               entity_id,
                               EntityLifeCycle.ALIVE,
                               None, False)

        # Done with iteration - clear the adds.
        self._entity_create.clear()

        return VerediHealth.HEALTHY

    def destruction(self,
                    time: 'TimeManager') -> VerediHealth:
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

            except EcsEntityError as error:
                self._log_exception(
                    error,
                    "EcsEntityError in destruction() for entity_id {}.",
                    entity_id)
                # TODO: put this entity in... jail or something? Delete?

            self._event_create(EntityLifeEvent,
                               entity_id,
                               EntityLifeCycle.DEAD,
                               None, False)

        # Done with iteration - clear the removes.
        self._entity_destroy.clear()

        return VerediHealth.HEALTHY
