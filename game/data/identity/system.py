# coding: utf-8

'''
System for handling Identity information (beyond the temporary in-game ID
numbers like MonotonicIds).

Papers, please.
'''


# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

# ---
# Typing
# ---
from typing import (TYPE_CHECKING,
                    Optional, Union, Any, MutableMapping,
                    List, Literal)
if TYPE_CHECKING:
    from veredi.base.context             import VerediContext


# ---
# Code
# ---
from veredi.logger                   import log
from veredi.base.const               import VerediHealth
from veredi.base.dicts               import BidirectionalDict
from veredi.data.config.registry     import register
from veredi.data.identity            import UserId, UserKey

# Game / ECS Stuff
from veredi.game.ecs.event           import EventManager
from veredi.game.ecs.time            import TimeManager
from veredi.game.ecs.component       import ComponentManager
from veredi.game.ecs.entity          import EntityManager, EntityLifeEvent

from veredi.game.ecs.const           import (SystemTick,
                                             SystemPriority)

from veredi.game.ecs.base.identity   import EntityId, ComponentId
from veredi.game.ecs.base.entity     import EntityLifeCycle
from veredi.game.ecs.base.system     import System
from veredi.game.ecs.base.exceptions import SystemErrorV

# Identity-Related Events & Components
from .event                          import IdentityRequest, IdentityResult
from .component                      import IdentityComponent


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

@register('veredi', 'game', 'identity', 'system')
class IdentitySystem(System):

    _SYNC_ENTITIES_REDUCED_TICK = 10

    def _define_vars(self):
        '''
        Instance variable definitions, type hinting, doc strings, etc.
        '''
        super()._define_vars()

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

    def _configure(self, context: 'VerediContext') -> None:
        '''
        Make our stuff from context/config data.
        '''
        self._component_type = IdentityComponent

        # ---
        # Health Stuff
        # ---
        self._required_managers = {
            TimeManager,
            EventManager,
            ComponentManager,
            EntityManager
        }

        # ---
        # Ticking Stuff
        # ---
        self._components = [
            # For ticking, we need the ones with IdentityComponents.
            # They're the ones with Identitys.
            # Obviously.
            IdentityComponent
        ]

        self._ticks = SystemTick.PRE  # | SystemTick.STANDARD
        self._set_reduced_tick_rate(SystemTick.PRE,
                                    self._SYNC_ENTITIES_REDUCED_TICK)

    @classmethod
    def dotted(klass: 'IdentitySystem') -> str:
        # klass._DOTTED magically provided by @register
        return klass._DOTTED

    # -------------------------------------------------------------------------
    # Direct Getters
    # -------------------------------------------------------------------------

    # Requried Game System, so we don't necessarily have to go through event
    # system or components...

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
    # System Registration / Definition
    # -------------------------------------------------------------------------

    def priority(self) -> Union[SystemPriority, int]:
        '''
        Returns a SystemPriority (or int) for when, relative to other systems,
        this should run. Highest priority goes firstest.
        '''
        return SystemPriority.LOW

    # -------------------------------------------------------------------------
    # Events
    # -------------------------------------------------------------------------

    def _subscribe(self) -> VerediHealth:
        '''
        Subscribe to any life-long event subscriptions here. Can hold on to
        event_manager if need to sub/unsub more dynamically.
        '''
        # IdentitySystem subs to:
        # - IdentityRequests - This covers:
        #   - CodeIdentityRequest
        #   - DataIdentityRequest - may want to ignore or delete these...?
        # - EntityLifeEvent - Entity gets created/destroyed.
        self._manager.event.subscribe(IdentityRequest,
                                      self.event_identity_req)

        self._manager.event.subscribe(EntityLifeEvent,
                                      self.event_entity_life)

        return VerediHealth.HEALTHY

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
            raise log.exception(
                None,
                SystemErrorV,
                "{} could not create IdentityComponent from no data {}.",
                self.__class__.__name__,
                component_data,
                context=context
            )

        retval = self._manager.create_attach(entity_id,
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
            raise log.exception(
                error,
                SystemErrorV,
                "{} could not get identity data from event {}. context: {}",
                self.__class__.__name__,
                event, event.context,
                context=event.context
            )

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

        entity = self._log_get_entity(event.id,
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
            id_comp = self.get(entity_id)
            if not id_comp:
                # No identity; make an empty one for now.

                # ------------------------------
                # !!!! NOTE !!!!
                # ------------------------------
                # This has caused some stupid/annoying unit test errors! If you
                # get here again because of them, this is probably a bad way of
                # doing things and we should rethink.
                log.ultra_mega_debug("No identity component for entity! "
                                     f"eid: {entity_id}")
                cid = self._create_component(entity_id,
                                             False,
                                             event.context)
                id_comp = self._manager.component.get(cid)

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

    def _update_pre(self) -> VerediHealth:
        '''
        Pre-update. For any systems that need to squeeze in something just
        before actual tick.
        '''
        health = VerediHealth.HEALTHY

        # ------------------------------
        # Full Tick Rate Start
        # ------------------------------

        # Nothing, at the moment.

        # ------------------------------
        # Full Tick Rate End
        # - - - - - - - - - - -
        if not self._is_reduced_tick(SystemTick.PRE):
            return self.health
        # - - - - - - - - - - -
        # !! REDUCED Tick Rate START !!
        # ------------------------------

        # Ok - our reduced tick is happening so make sure our dictionaries are
        # up to date with the entities.

        # ---
        # Update EntityIds, UserIds, UserKeys.
        # ---
        all_with_id = set()
        for entity in self._manager.entity.each_with(self._component_type):
            id_comp = self.get(entity.id)
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
        # !! REDUCED Tick Rate END !!
        # ------------------------------
        self.health = health
        return health

    # def _update(self) -> VerediHealth:
    #     '''
    #     Standard tick. Do we have ticky things to do?
    #     '''
    #     # Doctor checkup.
    #     if not self._health_ok_tick(SystemTick.STANDARD):
    #         return self._health_check(SystemTick.STANDARD)
    #
    #     log.critical('todo: a identity tick thingy?')
    #
    #     # for entity in self._wanted_entities(tick):
    #     #     # Check if entity in turn order has a (identity) action queued up
    #     #     # Also make sure to check if entity/component still exist.
    #     #     if not entity:
    #     #         continue
    #     #     component = component_mgr.get(IdentityComponent)
    #     #     if not component or not component.has_action:
    #     #         continue
    #
    #     #     action = component.dequeue
    #     #     log.debug("Entity {}, Comp {} has identity action: {}",
    #     #               entity, component, action)
    #
    #     #     # Check turn order?
    #     #     # Would that be, like...
    #     #     #   - engine.time_flow()?
    #     #     #   - What does PF2/Starfinder call it? Like the combat vs
    #     #     #     short-term vs long-term 'things are happening' modes...
    #
    #     #     # process action
    #     #     print('todo: a identity thingy', action)
    #
    #     return self._health_check(SystemTick.STANDARD)
