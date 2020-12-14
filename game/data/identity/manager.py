# coding: utf-8

'''
IdentityManager for... managing... IdentityComponents, UserIds, UserKeys, etc.
  - Identity Numbers beyond the temporary IDs like ComponentId, EntityId, etc.
  - Identity Names for entities, users, etc.

"Papers, please."
'''


# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

# ---
# Typing
# ---
from typing import (TYPE_CHECKING,
                    Optional, Union, Any, Type,
                    MutableMapping, Dict, Set, List, Literal)
from veredi.base.null              import Null, Nullable, NullNoneOr
if TYPE_CHECKING:
    from veredi.base.context       import VerediContext
    from ..ecs.meeting             import Meeting
    from ..ecs.event               import Event

# ---
# Code
# ---
from decimal                       import Decimal

from veredi.logger                 import log
from veredi.base.const             import VerediHealth
from veredi.base.dicts             import BidirectionalDict
from veredi.base.assortments       import DeltaNext
from veredi.debug.const            import DebugFlag
from veredi.data                   import background
from veredi.data.config.config     import Configuration
from veredi.data.config.registry   import register
from veredi.data.identity          import UserId, UserKey

# Game / ECS Stuff
from veredi.game.ecs.event         import EventManager, EcsManagerWithEvents
from veredi.game.ecs.time          import TimeManager
from veredi.game.ecs.component     import ComponentManager
from veredi.game.ecs.entity        import EntityManager, EntityLifeEvent

from veredi.game.ecs.const         import SystemTick

from veredi.game.ecs.base.identity import EntityId, ComponentId
from veredi.game.ecs.base.entity   import EntityLifeCycle
from veredi.game.ecs.base.system   import System
from veredi.game.ecs.exceptions    import EventError

# Identity-Related Events & Components
from .event                        import IdentityRequest, IdentityResult
from .component                    import IdentityComponent


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

class IdentityManager(EcsManagerWithEvents):
    '''
    "Manager" of Identities.

    The main point we're a "manager" when we could really just be a system or
    just let identities only exist as IdentityComponents: So that Systems can
    expect us to just exist as a directly callable manager instead of having to
    go through the event system or components...

    Another reason is that there is no requirement (currently [2020-12-09])
    that some piece of an Identity has to be tied to an IdentityComponent or
    Entity or anything.

    And identities will be tied to basically everything, so an event loop delay
    for basically everything seems like a decent thing to optimize out.
    '''

    _SYNC_ENTITIES_REDUCED_TICK = 10
    '''
    Do the reduced tick every this many ticks.
    '''

    def _define_vars(self):
        '''
        Instance variable definitions, type hinting, doc strings, etc.
        '''
        super()._define_vars()

        self._debug: Nullable[DebugFlag] = Null()
        '''
        Debug Flags.
        '''

        self._component_type: Type[IdentityComponent] = IdentityComponent
        '''
        The component type for storing ID info on an entity.
        '''

        # ------------------------------
        # Ticking
        # ------------------------------

        self._ticks: Optional[SystemTick] = None
        '''
        The ticks we desire to run in.

        Systems will always get the TICKS_START and TICKS_END ticks. The
        default _cycle_<tick> and _update_<tick> for those ticks should be
        acceptable if the system doesn't care.
        '''

        self._reduced_tick_rate: Optional[Dict[SystemTick, DeltaNext]] = {}
        '''
        If systems want to only do some tick (or part of a tick), they can put
        the tick and how often they want to do it here.

        e.g. if we want every 10th SystemTick.CREATION for checking that some
        data is in sync, set:
          TimeManager.set_reduced_tick_rate(SystemTick.CREATION, 10)
        '''

        # ------------------------------
        # Health
        # ------------------------------

        self._health_meter_event:   Optional['Decimal'] = None
        '''
        Store timing information for our timed/metered 'system isn't healthy'
        messages that fire off during event things.
        '''

        self._health_meter_update:  Optional['Decimal'] = None
        '''
        Stores timing information for our timed/metered 'system isn't healthy'
        messages that fire off during system tick things.
        '''

        # ------------------------------
        # Required Other Managers
        # ------------------------------
        self._entity: EntityManager = None
        '''
        The ECS Entity Manager.
        '''

        self._event: EventManager = None
        '''
        The ECS Event Manager.
        '''

        # ------------------------------
        # Quick Lookups
        # ------------------------------
        self._uids:  BidirectionalDict[EntityId,  UserId] = BidirectionalDict()
        '''
        UserId to EntityId and the inverse. Any number of EntityIds can be
        assigned the same UserId because familiars, companions, the DM...
        '''

        self._ukeys: BidirectionalDict[EntityId, UserKey] = BidirectionalDict()
        '''
        UserKey to EntityId and the inverse. Any number of EntityIds can be
        assigned the same UserKey because familiars, companions, the DM...
        '''

        self._anonymous: Set[EntityId] = set()
        '''
        Don't want any entities to not have identities, but currently nothing
        ensure that. So just keep a collection of the anonymous ones.

        TODO: Ensure that every entity gets some sort of IdentityComponent.
          - But do it in a way unit testing can easily manage.
            - Maybe an off/ignore flag.
        '''

    def __init__(self,
                 config:         Optional[Configuration],
                 time_manager:   TimeManager,
                 event_manager:  EventManager,
                 entity_manager: EntityManager,
                 debug_flags:    NullNoneOr[DebugFlag]) -> None:
        '''
        Make our stuff from context/config data.
        '''
        super().__init__()

        self._debug = debug_flags

        self._ticks = SystemTick.PRE  # Just PRE so far.
        time_manager.set_reduced_tick_rate(SystemTick.PRE,
                                           self._SYNC_ENTITIES_REDUCED_TICK,
                                           self._reduced_tick_rate)

        self._entity = entity_manager
        self._event = event_manager

    @classmethod
    def dotted(klass: 'IdentityManager') -> str:
        '''
        This manager's dotted label.
        '''
        return 'veredi.game.data.identity.manager'

    @property
    def _meeting(self) -> 'Meeting':
        '''
        Shortcut to getting the Meeting of Managers singleton.
        '''
        return background.manager.meeting

    # -------------------------------------------------------------------------
    # Direct Getters
    # -------------------------------------------------------------------------

    def user_id(self, entity_id: EntityId) -> Optional[UserId]:
        '''
        Gets the UserId assigned to the entity. Can be None.
        '''
        return self._uids.get(entity_id, None)

    def user_key(self, entity_id: EntityId) -> Optional[UserKey]:
        '''
        Gets the UserKey assigned to the entity. Can be None.
        '''
        return self._ukeys.get(entity_id, None)

    def user_id_to_entity_ids(self,
                              user_id: UserId) -> Optional[List[EntityId]]:
        '''
        Gets the list of EntityIds that are assigned to UserId. Can be None.
        '''
        return self._uids.inverse.get(user_id, None)

    def user_key_to_entity_ids(self,
                               user_key: UserKey) -> Optional[List[EntityId]]:
        '''
        Gets the list of EntityIds that are assigned to UserKey. Can be None.
        '''
        return self._ukeys.inverse.get(user_key, None)

    # -------------------------------------------------------------------------
    # IdentityComponent
    # -------------------------------------------------------------------------

    def component(self, entity_id: EntityId) -> Nullable['IdentityComponent']:
        '''
        Try to get entity. Try to get our IdentityComponent off entity.

        Return component or Null().
        '''
        # Not set up right.
        if not self._component_type:
            return Null()

        # Try to get entity (receive entity or Null), then return whatever from
        # attempt to get component (component or Null).
        entity = self._meeting.entity.get(entity_id)
        component = entity.get(self._component_type)
        return component

    # -------------------------------------------------------------------------
    # Health
    # -------------------------------------------------------------------------

    def _health_ok_event(self,
                         event: 'Event') -> bool:
        '''Check health, log if needed, and return True if able to proceed.'''
        if not self._healthy(self._meeting.time.engine_tick_current):
            meter = self._health_meter_event
            output_log, meter = self._meeting.time.metered(meter)
            self._health_meter_event = meter
            if output_log:
                msg = ("Dropping event {} - IdentityManager's health "
                       "isn't good enough to process.")
                kwargs = self._log_stack(None)
                self._log_warning(
                    f"HEALTH({self.health}): " + msg,
                    event,
                    context=event.context,
                    **kwargs)
            return False
        return True

    # -------------------------------------------------------------------------
    # Events
    # -------------------------------------------------------------------------

    def subscribe(self, event_manager: 'EventManager') -> VerediHealth:
        '''
        Subscribe to any life-long event subscriptions here. Can hold on to
        event_manager if need to sub/unsub more dynamically.
        '''
        # Use EventManager.is_subscribed() to make this re-entrant -
        # EventManager.subscribe() throws exceptions for repeated
        # subscriptions.

        # IdentityRequests cover:
        #   - DataIdentityRequest - IdentityComponent backed by repo data.
        #                         - Mainly game data.
        #   - CodeIdentityRequest - IdentityComponent backed by code.
        #                         - Mainly unit tests that avoid needing repo.
        if not self._event.is_subscribed(IdentityRequest,
                                         self.event_identity_req):
            self._event.subscribe(IdentityRequest,
                                  self.event_identity_req)

        # EntityLifeEvent:
        #   - Entity gets created/destroyed/etc.
        if not self._event.is_subscribed(EntityLifeEvent,
                                         self.event_entity_life):
            self._event.subscribe(EntityLifeEvent,
                                  self.event_entity_life)

        return VerediHealth.HEALTHY

    def _event_notify(self,
                      event:                      'Event',
                      requires_immediate_publish: bool = False) -> None:
        '''
        Calls our EventManager.notify(), if we have an EventManager.
        '''
        if not self._event:
            return
        self._event.notify(event,
                           requires_immediate_publish)

    def _create_component(
            self,
            entity_id:      EntityId,
            component_data: Union[MutableMapping[str, Any], Literal[False]],
            context:        'VerediContext') -> ComponentId:
        '''
        Asks ComponentManager to create the IdentityComponent for this entity.

        If component_data is False, will create an empty component. Otherwise
        the data must be valid.

        Returns created component's ComponentId or ComponentId.INVALID
        '''
        if component_data is False:
            # This is ok value - means "Make an empty IdentityComponent".
            pass

        elif not component_data:
            # Empty data is not ok. Throw an error.
            msg = (f"{self.__class__.__name__} could not create "
                   "IdentityComponent from no data.")
            error = EventError(msg,
                               context=context,
                               data={
                                   'entity_id': entity_id,
                                   'component_data': component_data,
                               })
            raise log.exception(error, msg,
                                context=context)

        # Create our component and attach to an entity.
        retval = self._meeting.create_attach(entity_id,
                                             IdentityComponent,
                                             context,
                                             data=component_data)
        return retval

    def request_creation(self,
                         event: IdentityRequest) -> ComponentId:
        '''
        Asks ComponentManager to create the IdentityComponent from this event.

        Returns created component's ComponentId or ComponentId.INVALID
        '''
        data = None
        try:
            data = event.data
        except AttributeError as error:
            msg = (f"{self.__class__.__name__} could not get identity "
                   "data from event.")
            error = EventError(msg,
                               context=event.context,
                               data={
                                   'event': event,
                               })
            raise log.exception(error, msg,
                                context=event.context)

        return self._create_component(event.id,
                                      data,
                                      event.context)

    def event_identity_req(self, event: IdentityRequest) -> None:
        '''
        Identity thingy want; make with the component plz.
        '''
        # Doctor checkup.
        if not self._health_ok_event(event):
            return

        entity = self._entity.get_with_log(
            f'{self.__class__.__name__}',
            event.id,
            event=event)
        if not entity:
            # Entity disappeared, and that's ok.
            return

        cid = self.request_creation(event)

        # Have EventManager create and fire off event for whoever wants the
        # next step.
        if (cid != ComponentId.INVALID):
            next_event = IdentityResult(event.id, event.type, event.context,
                                        component_id=cid)
            self._event_notify(next_event)

    def _user_ident_update(self,
                           entity_id: EntityId,
                           user_id:   Optional[UserId]  = None,
                           user_key:  Optional[UserKey] = None,
                           delete:    bool              = False) -> None:
        '''
        Update our entity/user-id and entity/user-key dicts.
        '''
        if delete:
            if entity_id in self._uids:
                del self._uids[entity_id]
            if entity_id in self._ukeys:
                del self._ukeys[entity_id]
            return

        elif user_id is None:  # TODO: user key check too: or user_key is None:
            # Not sure if this is a bad or ok thing. Maybe the unassigned
            # entities are AI or the DM or whatever.
            # Degrade to debug or "delete this block" if it's fine.
            # Upgrade to exception if never ok.
            log.critical("Entity {} is not assigned to a user: "
                         "user-id: {}, user-key: {}",
                         entity_id, user_id, user_key)

        self._uids[entity_id] = user_id
        self._ukeys[entity_id] = user_key

    def event_entity_life(self, event: EntityLifeEvent) -> None:
        '''
        Entity Life-cycle has changed enough that EntityManager has produced an
        event for it. See if we should add/remove from our dictionaries.
        '''
        # Doctor checkup.
        if not self._health_ok_event(event):
            return

        # ---
        # Deal with life-cycle transition.
        # ---
        entity_id = event.id
        entity_cycle = event.type
        if entity_cycle == EntityLifeCycle.INVALID:
            # INVALID should never come up, so... complain.
            log.error("EntityManager pushed Entity {} into {} life cycle. "
                      "Do not know how to handle this.",
                      entity_id, entity_cycle)
            self.health = VerediHealth.UNHEALTHY
            return

        elif entity_cycle == EntityLifeCycle.CREATING:
            # Don't care about CREATING - waiting for the ALIVE.
            pass

        elif entity_cycle == EntityLifeCycle.ALIVE:
            # They are now alive. Add to dictionaries.
            id_comp = self.component(entity_id)

            if not id_comp:
                # No identity; just store as anonymous for now...
                log.debug("Entity {} has entered life-cycle '{}' without any "
                          "identity_component. We have no current solution to "
                          "this conundrum... Recording as 'anonymous'.",
                          entity_id, entity_cycle)
                self._anonymous.add(entity_id)
                return

            # Now they have an IdentityComponent - update our dicts.
            self._user_ident_update(entity_id,
                                    user_id=id_comp.user_id,
                                    user_key=id_comp.user_key)

        elif (entity_cycle == EntityLifeCycle.DESTROYING
              or entity_cycle == EntityLifeCycle.DEAD):
            # Remove 'em from our dicts.
            self._user_ident_update(entity_id,
                                    delete=True)

        else:
            # Ignore.
            log.debug("Entity {} has entered life-cycle: {}. "
                      "We have nothing to do for that cycle.",
                      entity_id, entity_cycle)
            return

    # -------------------------------------------------------------------------
    # Game Update Loop/Tick Functions
    # -------------------------------------------------------------------------

    def update(self, tick: SystemTick) -> VerediHealth:
        '''
        Pre-update. For any systems that need to squeeze in something just
        before actual tick.
        '''
        # ------------------------------
        # Ignored Tick?
        # ------------------------------
        if not self._ticks or not self._ticks.has(tick):
            # Don't even care about my health since we don't even want
            # this tick.
            return VerediHealth.HEALTHY

        health = VerediHealth.HEALTHY

        # ------------------------------
        # Full Tick Rate: Start
        # ------------------------------

        # Nothing, at the moment.

        # ------------------------------
        # Full Tick Rate: End
        # - - - - - - - - - - -
        if not self._meeting.time.is_reduced_tick(
                tick,
                self._reduced_tick_rate):
            self.health = health
            return self.health
        # - - - - - - - - - - -
        # !! REDUCED Tick Rate: START !!
        # ------------------------------

        # Ok - our reduced tick is happening so make sure our dictionaries are
        # up to date with the entities.

        # ---
        # Update EntityIds, UserIds, UserKeys.
        # ---
        all_with_id = set()
        for entity in self._entity.each_with(self._component_type):
            id_comp = self.component(entity.id)
            if not id_comp:
                continue

            # Have an entity to update/add.
            self._user_ident_update(entity.id,
                                    user_id=id_comp.user_id,
                                    user_key=id_comp.user_key)
            all_with_id.add(entity.id)

        # ---
        # Remove EntityIds, UserIds, UserKeys.
        # ---
        for entity_id in self._uids:
            if entity_id in all_with_id:
                continue

            # EntityId wasn't present in updated (so they don't exist now or
            # their IdentityComponent doesn't), but is in our dict. Remove from
            # our dict to sync up.
            self._user_ident_update(entity_id,
                                    delete=True)

        # This shouldn't find anyone new... Assuming the dicts are in sync and
        # all entities with UserKeys also have UserIds.
        for entity_id in self._ukeys:
            if entity_id in all_with_id:
                continue

            # EntityId wasn't present in updated (so they don't exist now or
            # their IdentityComponent doesn't), but is in our dict. Remove from
            # our dict to sync up.
            ukey = self.user_key(entity_id)
            self._user_ident_update(entity_id,
                                    delete=True)
            log.warning("Entity/User sync: UserId and UserKey dicts were out "
                        "of sync. Entity {} had a UserKey {} but no UserId.",
                        entity_id, ukey)
            health = health.update(VerediHealth.UNHEALTHY)

        # ------------------------------
        # !! REDUCED Tick Rate: END !!
        # ------------------------------
        self.health = health
        return health
