# coding: utf-8

'''
Mediator System for Veredi.

Handles:
  - InputSystem <- MediatorServer
  - OutputSystem -> MediatorServer
  - Other things possibly?

The MediatorServer and game run in separate processes. This runs as a system of
the game (and in the game's process), handling the IPC between the game and the
MediatorServer.
'''


# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

# ---
# Typing
# ---
from typing import (TYPE_CHECKING,
                    Optional, Union, Any, Type, Awaitable, Iterable,
                    Set, Tuple, Literal)
from veredi.base.null import Null, null_to_none
if TYPE_CHECKING:
    from decimal                   import Decimal

    from veredi.base.context       import VerediContext
    from veredi.game.ecs.component import ComponentManager
    from veredi.game.ecs.entity    import EntityManager
    from veredi.game.ecs.manager   import EcsManager


# ---
# Code
# ---

# Basic Stuff
from veredi.data                         import background

from veredi.logger                       import log, log_client

from veredi.base.const                   import VerediHealth
from veredi.data.config.registry         import register
from veredi.data.config.context         import ConfigContext

from veredi.data.config.config import Configuration
from veredi.base.identity      import MonotonicId, MonotonicIdGenerator


# Game / ECS Stuff
from veredi.game.ecs.event               import EventManager
from veredi.game.ecs.time                import TimeManager, MonotonicTimer

from veredi.game.ecs.const               import (SystemTick,
                                                 SystemPriority)

from veredi.game.ecs.base.system         import System
from veredi.game.ecs.base.component      import Component
from veredi.game.data.identity.component import IdentityComponent
from veredi.game.data.identity.system    import IdentitySystem


from ..input.context                            import InputContext
from ..input                                   import sanitize
from ..input.parse                              import Parcel
from ..input.command.commander                  import Commander
from ..input.history.history                    import Historian


# Mediator Stuff
from .event                              import (MediatorSendEvent,
                                                 MediatorReceiveEvent)
from .context                  import MediatorContext, MessageContext
from .message                  import Message, MsgType
from .payload.logging          import LogPayload, LogField

# Multi-Processing Stuff
from veredi.parallel import multiproc

# TODO [2020-06-27]: Better place to do these registrations.
import veredi.zest.debug.registration


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Mediator Server Entry
# -----------------------------------------------------------------------------


def _start_server(comms: multiproc.SubToProcComm,
                  context: 'VerediContext') -> None:
    '''
    Entry function for our mediator server.

    Basically create mediator from config and call its `start()`.
    '''

    # ------------------------------
    # Set-Up
    # ------------------------------

    # ---
    # Config
    # ---
    comms = ConfigContext.subproc(context)
    if not comms:
        raise log.exception(
            "MediatorServer requires a SubToProcComm; received None.")

    config = background.config.config
    if not config:
        raise background.config.exception(
            context,
            None,
            "Cannot configure a MediatorServer without a Configuration in the "
            "background context.",
            self.__class__.__name__)

    # ---
    # Logging
    # ---
    log_level = ConfigContext.log_level(context)
    lumberjack = log.get_logger(comms.name,
                                min_log_level=log_level)

    multiproc._sigint_ignore()
    log_client.init(log_level)

    # ------------------------------
    # Create & Start
    # ------------------------------

    mediator = config.make(context,
                           'server',
                           'mediator',
                           'type')
    mediator.start()


# -----------------------------------------------------------------------------
# System
# -----------------------------------------------------------------------------


@register('veredi', 'interface', 'mediator', 'system')
class MediatorSystem(System):

    MSG_MAX_PER_UPDATE: int = 20
    '''
    Default max messages to pull from MediatorServer IPC pipe and process per
    update tick. Can be overridden by config data.

    Multiply by however many game-loop ticks it runs in to figure out total
    max per full tick cycle.
    '''

    MSG_TYPE_SUPPORTED = frozenset({
        MsgType.TEXT,
        MsgType.ENCODED,
        MsgType.CODEC,
    })

    TIME_APOPTOSIS_SEC = 10.0
    '''
    We request this many seconds to let apoptosis run. We can only request it,
    not assume we'll get it all.
    '''

    TIME_PROCESS_START_SEC = 1.0
    '''
    We request this many seconds to let process warm up. We can only request
    it, not assume we'll get it all.
    '''

    def _configure(self, context: 'VerediContext') -> None:
        '''
        Make our stuff from context/config data.
        '''

        self.server: multiproc.ProcToSubComm = None
        '''Our MediatorServer process IPC & info object.'''

        self._msg_id: MonotonicIdGenerator = MonotonicId.generator()
        '''ID generator for creating Mediator messages.'''

        self._component_type: Type[Component] = None
        '''Don't have a component type for mediator right now.'''

        # ---
        # Health Stuff
        # ---
        self._required_managers: Optional[Set[Type['EcsManager']]] = {
            # TimeManager,
            EventManager
        }
        self._health_meter_update: Optional['Decimal'] = None
        self._health_meter_event:  Optional['Decimal'] = None

        # ---
        # Ticking Stuff
        # ---
        self._components: Optional[Set[Type[Component]]] = None

        # Just the post-setup; pre-game-loop tick for now for set-up.
        self._ticks: SystemTick = (
            # ---
            # Game Set-Up Ticks:
            # ---
            # Spawn our sub-process here.
            SystemTick.INTRA_SYSTEM

            # ---
            # Game Running Ticks:
            # ---
            # Use just-before and just-after standard for doing communication?
            # Event stuff can happen any time so should be ok? Maybe?
            | SystemTick.PRE
            | SystemTick.POST
        )

        self._msg_max_per_update: int = self.MSG_MAX_PER_UPDATE
        '''
        Max messages to pull from MediatorServer IPC pipe and process per
        update tick.

        Multiply by however many game-loop ticks it runs in to figure out
        total max per full tick cycle.
        '''

        # ---
        # Context Stuff
        # ---
        config = background.config.config
        if not config:
            raise background.config.exception(
                context,
                None,
                "Cannot configure {} without a Configuration in the "
                "supplied context.",
                self.__class__.__name__)

        # ---
        # Sub-Process: Mediator Server Create & Config
        # ---
        self._configure_mediator_server(context, config)

        # ---
        # More Context Stuff
        # ---
        # Create our background context now that we have enough info from
        # config.
        bg_data, bg_owner = self._background
        background.mediator.set('system',
                                bg_data,
                                bg_owner)
        # TODO: get mediator server's background data from it? Or does it set
        # itself?
        # background.mediator.set('server'?,
        #                         server_bg_data,
        #                         server_bg_data_owner)

    def _configure_mediator_server(self, context, config):
        '''
        Create / Set-Up Mediator Server according to config data.
        '''

        self.dotted_server = config.get('server',
                                        'mediator',
                                        'type')
        # Get log_level if we have it, if not: convert null to none.
        initial_log_level = null_to_none(ConfigContext.log_level(context))
        # Use SystemManager's DebugFlag setting?
        debug_flags = self._manager.system.debug
        # Grab ut flag from background?
        ut_flagged = background.testing.get_unit_testing()

        # ...And get ready for running our sub-proc.
        self.server = multiproc.set_up(
            proc_name=self.dotted_server,
            config=config,
            context=context,
            entry_fn=_start_server,
            initial_log_level=initial_log_level,
            debug_flags=debug_flags,
            unit_testing=ut_flagged)

    @property
    def _background(self):
        '''
        Get background data for background.mediator.set().
        '''
        self._bg = {
            'dotted': self.dotted,
            'server': self.dotted_server,
        }
        return self._bg, background.Ownership.SHARE

    @property
    def dotted(self) -> str:
        # self._DOTTED magically provided by @register
        return self._DOTTED

    # -------------------------------------------------------------------------
    # System Registration / Definition
    # -------------------------------------------------------------------------

    def priority(self) -> Union[SystemPriority, int]:
        '''
        Returns a SystemPriority (or int) for when, relative to other systems,
        this should run. Highest priority goes firstest.
        '''
        # TODO: Do I want some sort of "bracketed-outer" priority so that the
        # server can run first-ish (HIGH priority) in PRE but last-ish (LOW
        # priority) in POST? Or "bracketed-inner" idk. Or HIGH_LOW for a double
        # run per... idk.
        return SystemPriority.HIGH

    # -------------------------------------------------------------------------
    # System Health
    # -------------------------------------------------------------------------

    def _health_check(self,
                      tick: SystemTick,
                      current_health: VerediHealth = VerediHealth.HEALTHY
                      ) -> VerediHealth:
        '''
        Tracks our system health. Returns either `current_health` or something
        worse from what all we track.
        '''
        # ---
        # Managers
        # ---
        manager_health = self._manager.healthy(self._required_managers)

        # ---
        # MediatorServer / multiproc
        # ---
        mediator_health = VerediHealth.INVALID
        multiproc_health = VerediHealth.INVALID
        if not self.server:
            # Really need server to be able to do anything.
            mediator_health = VerediHealth.FATAL
        else:
            multiproc_health = self.server.healthy(phase=self._life_cycle)

        # Set our state to whatever's worse and return that.
        self._health = self._health.update(current_health,
                                           manager_health,
                                           mediator_health,
                                           multiproc_health)
        return self._health_check(tick, self._health)

    # -------------------------------------------------------------------------
    # Events
    # -------------------------------------------------------------------------

    def _subscribe(self) -> VerediHealth:
        '''
        Subscribe to any life-long event subscriptions here. Can hold on to
        event_manager if need to sub/unsub more dynamically.
        '''
        # MediatorSystem subs to:
        # - MediatorSendEvent
        self._manager.event.subscribe(MediatorSendEvent,
                                      self.event_to_message)

        return VerediHealth.HEALTHY

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    @property
    def _identity(self) -> IdentitySystem:
        '''
        Get the IdentitySystem.
        '''
        return self._manager.system.get(IdentitySystem)

    # -------------------------------------------------------------------------
    # Data Flow: Game -> MediatorServer
    # -------------------------------------------------------------------------

    def event_to_message(self, event: MediatorSendEvent) -> None:
        '''
        MediatorSystem needs to turn this event into a Message and Context,
        then push into the MediatorServer's IPC pipe.
        '''
        # ---
        # Doctor checkup.
        # ---
        if not self._healthy(self._manager.time.engine_tick_current):
            self._health_meter_event = self._health_log(
                self._health_meter_event,
                log.Level.WARNING,
                "HEALTH({}): Dropping event {} - our system health "
                "isn't good enough to process.",
                self.health, event,
                context=event.context)
            return

        # ------------------------------
        # Get identity.
        # ------------------------------
        entity = self._log_get_entity(event.id,
                                      event=event)
        if not entity:
            # Entity disappeared, and that's ok.
            return

        # Normal for entities or components to go away, but
        # IdentityComponent should be for the entity's lifetime, and we
        # need UserId/UserKey from somewhere.
        ident = entity.get(IdentityComponent)
        if not ident:
            log.warning("Cannot send event; entity has no "
                        "IdentityComponent to demark receipient: {}",
                        event)
            return
        user_id = ident.user_id
        user_key = ident.user_key
        if not user_id:
            log.warning("Cannot send event; entity's IdentityComponent has no "
                        "UserId/UserKey to demark receipient: "
                        "{}, {}. event: {}",
                        user_id, user_key, event)
            # Normal for entities or components to go away, but
            # IdentityComponent should be for the entity's lifetime, and we
            # need UserId/UserKey from somewhere.
            return

        # ------------------------------
        # Create Message.
        # ------------------------------
        send_id = self._msg_id.next()

        # Figure out message type.
        # self._decide_msg_type(event.payload, entity, user_id)???
        msg_type = MsgType.CODEC
        if isinstance(event.payload, str):
            msg_type = MsgType.TEXT
        elif isinstance(event.payload, dict):
            msg_type = MsgType.ENCODE

        send_msg = Message(send_id,
                           msg_type,
                           user_id=user_id,
                           user_key=user_key)
        send_ctx = event.context

        # ------------------------------
        # Send message to MediatorServer
        # ------------------------------
        self.server.send(send_msg, send_ctx)

    # -------------------------------------------------------------------------
    # Data Flow: MediatorServer -> Game
    # -------------------------------------------------------------------------

    def _error_check_msg(self,
                         message: Message,
                         context: MessageContext) -> bool:
        '''
        Make sure we have a MsgType we care about.

        TODO [2020-09-22]: Should MediatorServer be responsible for converting
        and we just pass it on?
        '''
        # Other MsgTypes are invalid for the Game so we error on them.
        if message.type not in self.MSG_TYPE_SUPPORTED:
            msg = ("Invalid MsgType. Can only support: "
                   f"{self.MSG_TYPE_SUPPORTED}. "
                   f"Got: {message.type}.")
            raise log.exception(ValueError(msg, message.type),
                                None,
                                msg,
                                context=context)
        return True

    def _get_payload(self,
                     message: Message,
                     context: MessageContext) -> Any:
        '''
        Returns payload from message.

        Currently super simple. Maybe more complex when/if more payloads like
        LogPayload show up.
        '''
        return message.payload

    def validate_message(self,
                         message: Message,
                         context: MessageContext) -> Optional[Any]:
        '''
        Error check message and return payload object if valid.

        Raises error if not valid:
          - ValueError: unhandled message.type
        '''
        if not self._error_check_msg(message, context):
            return None

        return self._get_payload(message, context)

    def message_to_event(self,
                         message: Message,
                         context: MessageContext) -> None:
        '''
        Take `message` and `context` from MediatorServer, process into an
        event, and publish.
        '''
        # ------------------------------
        # UserId/Key -> EntityId
        # ------------------------------
        # Need to figure out who to tag this event we're creating for.
        #
        # Sometimes it comes with an entity_id,
        # sometimes we may need to figure one out, and
        # sometimes maybe it's not an entity-targeted message, maybe?
        entity_id = message.entity_id
        if not entity_id:
            # More than one entity can be assigned to a user, so we'll get back
            # a list. If there's only one, we'll assign that one. If multiple
            # ...I don't know right now. Probably push the whole list into the
            # context regardless.
            id_list = self._identity.user_id_to_entity_ids(message.user_id)
            context.entity_ids = id_list

            if len(id_list) == 1:
                entity_id = context.entity_ids[0]

        # ------------------------------
        # Payload
        # ------------------------------
        # Check message and get payload.
        event_payload = self.validate_message(message, context)

        # Build event.
        event = MediatorReceiveEvent(entity_id,
                                     # TODO: MsgType? Something else?
                                     message.type,
                                     context,
                                     event_payload)

        # ------------------------------
        # Publish Event
        # ------------------------------
        self._manager.event.notify(event)

    # -------------------------------------------------------------------------
    # Game Start-Up Tick Functions
    # -------------------------------------------------------------------------

    def _update_intra_system(self,
                             timer: 'MonotonicTimer') -> VerediHealth:
        '''
        Start the mediator, do any other start-up needed here.
        '''
        # ---
        # Doctor checkup.
        # ---
        if not self._healthy(SystemTick.INTRA_SYSTEM):
            self._health_meter_update = self._health_log(
                self._health_meter_update,
                log.Level.WARNING,
                "HEALTH({}): Skipping tick {} - our system health "
                "isn't good enough to process.",
                self.health, SystemTick.INTRA_SYSTEM)
            return self._health_check(SystemTick.INTRA_SYSTEM)

        # ------------------------------
        # Check if done starting up.
        # ------------------------------
        if self.server.process.is_alive():
            # Give our process a bit of time to start up.
            # TODO [2020-09-25]: Could send/recv a test message to see when it
            # actually is ready.
            if not timer.timed_out(self.TIME_PROCESS_START_SEC):
                return VerediHealth.PENDING
            else:
                return VerediHealth.HEALTHY

        # ------------------------------
        # Start up our process.
        # ------------------------------
        self.server.process.start()

        # Did a thing this tick so say we're PENDING...
        return VerediHealth.PENDING

    # -------------------------------------------------------------------------
    # Game Loop Tick Functions
    # -------------------------------------------------------------------------

    def _get_external_messages(self,
                               max_messages: Optional[int] = None) -> None:
        '''
        Read messages from MediatorServer, process them into events for game,
        and notify to EventManager.

        If `max_messages` is not supplied, will default to
        `self._msg_max_per_update`.
        '''
        if max_messages is None:
            max_messages = self._msg_max_per_update
        for i in range(max_messages):
            # No data in pipe so we're done early.
            if not self.server.has_data():
                break

            # Get message, context and process it.
            message, context = self.server.recv()
            self.message_to_event(message, context)

    def _update_pre(self,
                    time_mgr:      TimeManager,
                    component_mgr: 'ComponentManager',
                    entity_mgr:    'EntityManager') -> VerediHealth:
        '''
        Pre-update. For any systems that need to squeeze in something just
        before actual tick.
        '''
        # ---
        # Doctor checkup.
        # ---
        if not self._healthy(SystemTick.PRE):
            self._health_meter_update = self._health_log(
                self._health_meter_update,
                log.Level.WARNING,
                "HEALTH({}): Skipping tick {} - our system health "
                "isn't good enough to process.",
                self.health, SystemTick.PRE)
            return self._health_check(SystemTick.PRE)

        # ------------------------------
        # Process messages in pipe.
        # ------------------------------
        self._get_external_messages()
        return self._health_check(SystemTick.PRE)

    def _update_post(self,
                     time_mgr:      TimeManager,
                     component_mgr: 'ComponentManager',
                     entity_mgr:    'EntityManager') -> VerediHealth:
        '''
        Post-update. For any systems that need to squeeze in something just
        after actual tick.
        '''
        # ---
        # Doctor checkup.
        # ---
        if not self._healthy(SystemTick.POST):
            self._health_meter_update = self._health_log(
                self._health_meter_update,
                log.Level.WARNING,
                "HEALTH({}): Skipping tick {} - our system health "
                "isn't good enough to process.",
                self.health, SystemTick.POST)
            return self._health_check(SystemTick.POST)

        # ------------------------------
        # Process messages in pipe.
        # ------------------------------
        self._get_external_messages()
        return self._health_check(SystemTick.POST)

    # -------------------------------------------------------------------------
    # Apoptosis Functions
    # -------------------------------------------------------------------------

    def apoptosis_time_desired(self) -> Optional[float]:
        '''
        If a system wants some minimum time, they can override this function.
        This is only a request, though. The SystemManager or Engine may not
        grant it.
        '''
        return self.TIME_APOPTOSIS_SEC

    def _apoptosis_done_check(self) -> Union[Literal[False], VerediHealth]:
        '''
        Are we done dying yet?

        Runs multiproc tear_down if so.

        Returns:
          - `False` if still running.
          - VerediHealth result if done dying.
        '''
        # Nope; still alive.
        if self.server.process.is_alive():
            return False

        # ---
        # How dead is it?
        # ---
        # Well... It's dead, so do tear_down_end before returning health.
        multiproc.nonblocking_tear_down_end(self.server)

        healthy_exit = self.server.exitcode_healthy(
            VerediHealth.APOPTOSIS_SUCCESSFUL,
            VerediHealth.APOPTOSIS_FAILURE)
        return healthy_exit

    def _cycle_apoptosis(self) -> VerediHealth:
        '''
        System is being cycled into apoptosis state from current state.
        Current state is still set in self._life_cycle.
        '''
        # Use the non-blocking multiproc functions!

        # ------------------------------
        # Start our Graceful Death.
        # ------------------------------
        self._health = self._health.update(VerediHealth.APOPTOSIS)

        # Start the teardown... We'll wait on it during _update_apoptosis().
        multiproc.nonblocking_tear_down_start(self.server)

        # TODO: Just return APOPTOSIS even if our health is different?
        # Not sure...
        return VerediHealth.APOPTOSIS

    def _update_apoptosis(self,
                          time_mgr:      TimeManager,
                          component_mgr: 'ComponentManager',
                          entity_mgr:    'EntityManager') -> VerediHealth:
        '''
        Structured death phase. System should be responsive until it the next
        phase, but should be doing stuff for shutting down, like saving off
        data, etc.

        Default is "do nothing and return done."
        '''
        # Set to failure state if over time.
        if self._manager.time.is_timed_out(
                None,
                self.apoptosis_time_desired(),
                use_engine_timer=True):
            # Don't care about tear_down_end result; we'll check it with
            # exitcode_healthy().
            multiproc.nonblocking_tear_down_end(self.server)
            # Update with exitcode's health, and...
            self._health = self._health.update(
                self.server.exitcode_healthy(
                    VerediHealth.APOPTOSIS_SUCCESSFUL,
                    VerediHealth.APOPTOSIS_FAILURE))

            # Update with our health (failed due to overtime), and return.
            self._health = self._health.update(
                VerediHealth.APOPTOSIS_FAILURE)
            return self.health

        # Else we still have time to wait.
        multiproc.nonblocking_tear_down_wait(self.server,
                                             log_enter=True)
        done = self._apoptosis_done_check()
        if done is not False:
            # Update with done's health since we're done.
            self._health = self._health.update(done)
        else:
            # Update health with APOPTOSIS, since we're in progress.
            self._health = self._health.update(VerediHealth.APOPTOSIS)

        return self.health
