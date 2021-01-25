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
                    Optional, Union, Any, Type, Awaitable, Callable,
                    Iterable, Set, Tuple, Literal)
from veredi.base.null import Null, null_to_none
if TYPE_CHECKING:
    from decimal                   import Decimal

    from veredi.game.ecs.component import ComponentManager
    from veredi.game.ecs.entity    import EntityManager
    from veredi.game.ecs.manager   import EcsManager


# ---
# Code
# ---

# Basic Stuff
from veredi.data                         import background
from veredi.base.context                 import VerediContext

from veredi.logger                       import log, log_client
from veredi.debug.const                  import DebugFlag

from veredi.base.const                   import VerediHealth
from veredi.data.config.registry         import register
from veredi.data.config.context          import ConfigContext

from veredi.base.identity                import (MonotonicId,
                                                 MonotonicIdGenerator)


# Game / ECS Stuff
from veredi.game.ecs.event               import EventManager
from veredi.game.ecs.time                import TimeManager, MonotonicTimer

from veredi.game.ecs.const               import (SystemTick,
                                                 SystemPriority,
                                                 tick_health_init)

from veredi.game.ecs.base.system         import System
from veredi.game.ecs.base.component      import Component
from veredi.game.data.identity.component import IdentityComponent
from veredi.game.data.identity.manager   import IdentityManager

from ..user                              import UserPassport
from ..output.envelope                   import Envelope


# Mediator Stuff
from .event                              import (GameToMediatorEvent,
                                                 MediatorToGameEvent)
from .context                            import MediatorContext, MessageContext
from .const                              import MsgType
from .message                            import Message, ConnectionMessage

# Multi-Processing Stuff
from veredi.parallel                     import multiproc

# TODO [2020-06-27]: Better place to do these registrations.
import veredi.zest.debug.registration


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Mediator Server Entry
# -----------------------------------------------------------------------------


def _start_server(comms: multiproc.SubToProcComm,
                  context: VerediContext) -> None:
    '''
    Entry function for our mediator server.

    Basically create mediator from config and call its `start()`.
    '''

    # ------------------------------
    # Set-Up
    # ------------------------------
    log_level = ConfigContext.log_level(context)
    lumberjack = log.get_logger(comms.name,
                                min_log_level=log_level)
    lumberjack.setLevel(log_level)
    log.debug(f"_start_server: {comms.name} {log_level}",
              veredi_logger=lumberjack)

    # ---
    # Config
    # ---
    comms = ConfigContext.subproc(context)
    if not comms:
        raise log.exception(
            TypeError,
            "MediatorServer requires a SubToProcComm; received None.")

    config = background.config.config(
        '_start_server',
        'veredi.interface.mediator._start_server',
        context)

    # ---
    # Ignore Ctrl-C. Have parent process deal with it and us.
    # ---
    multiproc._sigint_ignore()

    # ---
    # Logging
    # ---
    # Do not set up log_client here - multiproc does that.

    # ------------------------------
    # Create & Start
    # ------------------------------

    log.debug(f"MediatorSystem's _start_server for {comms.name} "
              "starting MediatorServer...",
              veredi_logger=lumberjack)
    mediator = config.create_from_config('server',
                                         'mediator',
                                         'type',
                                         context=context)
    mediator.start()
    log.debug(f"MediatorSystem's _start_server for {comms.name} done.",
              veredi_logger=lumberjack)


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

    MSG_TYPE_SELF = frozenset({
        MsgType.CONNECT,
        MsgType.DISCONNECT,
    })
    '''
    Messages between MediatorServer & MediatorSystem will use these types.
    '''

    MSG_TYPE_GAME = frozenset({
        MsgType.TEXT,
        MsgType.ENCODED,
    })
    '''
    Messages between Mediator (Server or Client-via-Server) & Game will use
    these types.
    '''

    MSG_TYPE_IGNORE_WHILE_DYING = frozenset({
        # Testing / Non-Standard
        MsgType.IGNORE,
        MsgType.PING,
        MsgType.ECHO,
        MsgType.ECHO_ECHO,
        MsgType.LOGGING,

        # Connections
        MsgType.CONNECT,
        MsgType.DISCONNECT,

        # ACKs
        MsgType.ACK_CONNECT,
        MsgType.ACK_ID,
    })
    '''
    Messages of these types from client to server will be ignored from
    SystemTick.APOPTOSIS onwards.
    '''

    TIME_TICKS_END_SEC = 10.0
    '''
    We request this many seconds to let apoptosis run. We can only request it,
    not assume we'll get it all.
    '''

    TIME_PROCESS_START_SEC = 1.0
    '''
    We request this many seconds to let process warm up. We can only request
    it, not assume we'll get it all.
    '''

    def _configure(self, context: VerediContext) -> None:
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
        config = background.config.config(self.__class__.__name__,
                                          self.dotted(),
                                          context)

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
            'dotted': self.dotted(),
            'server': self.dotted_server,
        }
        return self._bg, background.Ownership.SHARE

    @classmethod
    def dotted(klass: 'MediatorSystem') -> str:
        # klass._DOTTED magically provided by @register
        return klass._DOTTED

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
            multiproc_health = self.server.healthy(self._life_cycle)

        # Set our state to whatever's worse and return that.
        self._health = self._health.update(current_health,
                                           manager_health,
                                           mediator_health,
                                           multiproc_health)
        return self.health

    # -------------------------------------------------------------------------
    # Events
    # -------------------------------------------------------------------------

    def _subscribe(self) -> VerediHealth:
        '''
        Subscribe to any life-long event subscriptions here. Can hold on to
        event_manager if need to sub/unsub more dynamically.
        '''
        # MediatorSystem subs to:
        # - GameToMediatorEvent
        self._manager.event.subscribe(GameToMediatorEvent,
                                      self.event_to_message)

        return VerediHealth.HEALTHY

    # -------------------------------------------------------------------------
    # Data Flow: Game -> MediatorServer
    # -------------------------------------------------------------------------

    def event_to_message(self, event: GameToMediatorEvent) -> None:
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
        # Assume IdentityManager exists.
        entity_id = event.id
        user_id = self._manager.identity.user_id(entity_id)
        user_key = self._manager.identity.user_key(entity_id)
        if not user_id:
            self._log_warning("Cannot send event; IdentityManager didn't have "
                              "a user_id for the entity to demark receipient: "
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
        msg_type = MsgType.TEXT
        if isinstance(event.payload, Envelope):
            msg_type = MsgType.ENVELOPE

        elif isinstance(event.payload, str):
            msg_type = MsgType.TEXT

        elif isinstance(event.payload, dict):
            msg_type = MsgType.ENCODE

        send_msg = Message(send_id,
                           msg_type,
                           user_id=user_id,
                           user_key=user_key,
                           entity_id=entity_id,
                           # Don't Forget the Payload...
                           #            >.>
                           payload=event.payload)

        send_ctx = event.context

        # ------------------------------
        # Send Message to MediatorServer
        # ------------------------------
        self.server.send(send_msg, send_ctx)

    # -------------------------------------------------------------------------
    # Data Flow: MediatorServer -> Game
    # -------------------------------------------------------------------------

    def _message_connect(self,
                         message: ConnectionMessage,
                         context: MessageContext) -> None:
        '''
        User is changing connection state (CONNECT, DISCONNECT). Add or remove
        them from connected as indicated.
        '''
        if message.type == MsgType.CONNECT:
            # Create UserPassport for our connected user, add to background so
            # other systems can translate user_id to useful info (e.g. entity)?
            user = UserPassport(message.user_id,
                                message.user_key,
                                message.connection)
            background.users.add_connected(user)
            return

        elif message.type == MsgType.DISCONNECT:
            # Remove user from background data.
            background.users.remove_connected(message.user_id)
            return

        # Else it's somehow valid but we don't know how...
        msg = ("Don't know how to process ConnectionMessage of type "
               f"'{message.type}': {message}")
        raise self._log_exception(
            ValueError(msg),
            msg,
            context=context)

    def _message_to_event(self,
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
            id_list = self._manager.identity.user_id_to_entity_ids(message.user_id)
            context.entity_ids = id_list

            if id_list and len(id_list) == 1:
                entity_id = context.entity_ids[0]

        # ------------------------------
        # Payload
        # ------------------------------
        # Check message and get payload.
        event_payload = self._get_payload(message, context)

        # Build event.
        event = MediatorToGameEvent(entity_id,
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

    def _update_intra_system(self) -> VerediHealth:
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
            if not self._manager.time.is_timed_out(None,
                                                   self.TIME_PROCESS_START_SEC):
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
    # Server Message Helpers
    # -------------------------------------------------------------------------

    def _error_check_msg(self,
                         message:    Message,
                         context:    MessageContext) -> bool:
        '''
        Make sure we have a MsgType we care about.

        TODO [2020-09-22]: Should MediatorServer be responsible for converting
        and we just pass it on?
        '''
        if message.type in self.MSG_TYPE_GAME:
            return True

        elif message.type in self.MSG_TYPE_SELF:
            return True

        # Other MsgTypes are invalid for the Game so we error on them.

        # Frozen set gets printed as: "frozenset({...", which messes up
        # log's bracket formatter at the moment [2020-10-24], so I guess
        # format the message twice.
        msg = "Invalid MsgType '{}'. Can only support: {}"
        raise self._log_exception(
            ValueError(msg.format(message.type,
                                  self.MSG_TYPE_SUPPORTED),
                       message),
            msg,
            message.type,
            self.MSG_TYPE_SUPPORTED,
            context=context)

    def _get_payload(self,
                     message: Message,
                     context: MessageContext) -> Any:
        '''
        Returns payload from message.

        Currently super simple. Maybe more complex when/if more payloads like
        LogPayload show up.
        '''
        return message.payload

    def _deliver_message(self,
                         message: Message,
                         context: MessageContext) -> None:
        '''
        Take `message` and `context` from MediatorServer, decides if it is for
        us or the game, then forwards to the proper message processing
        function.
        '''
        if not self._error_check_msg(message, context):
            return

        if message.type in self.MSG_TYPE_SELF:
            self._message_internal(message, context)
            return

        elif message.type in self.MSG_TYPE_GAME:
            self._message_to_event(message, context)
            return

        # Else it's somehow valid but we don't know how...
        msg = ("Valid MsgType but no message processor for it. "
               f"MsgType: {message.type}.")
        raise self._log_exception(
            ValueError(msg),
            msg,
            context=context)

    def _message_internal(self,
                          message: Message,
                          context: MessageContext) -> None:
        '''
        Take `message` and `context` from MediatorServer and deal with their
        contents ourselves.
        '''
        if message.msg_id == Message.SpecialId.CONNECT:
            self._message_connect(message, context)
            return

        # Else it's somehow valid but we don't know how...
        msg = f"Don't know how to process message: {message}"
        raise self._log_exception(
            ValueError(msg),
            msg,
            context=context)

    def _get_external_messages(
            self,
            message_fn:   Callable[[Message, VerediContext], bool] = None,
            max_messages: Optional[int]                                 = None
    ) -> None:
        '''
        Read messages from MediatorServer, process them into events for game,
        and notify to EventManager.

        If `message_fn` is supplied and a message exists, this calls
        `message_fn(message, context)` and expects a return of:
            True  - deliver message
            False - drop message

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
            # Delivery can be vetoed by message_fn.
            if not message_fn or message_fn(message, context):
                self._deliver_message(message, context)

    # -------------------------------------------------------------------------
    # Game Loop Tick Functions
    # -------------------------------------------------------------------------

    def _update_pre(self) -> VerediHealth:
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

    def _update_post(self) -> VerediHealth:
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
    # Life-Cycle Functions
    # -------------------------------------------------------------------------

    def timeout_desired(self, cycle: SystemTick) -> Optional[float]:
        '''
        If a system wants some minimum time, they can override this function.
        This is only a request, though. The SystemManager or Engine may not
        grant it.
        '''
        if cycle == SystemTick.APOPTOSIS or cycle  == SystemTick.APOCALYPSE:
            return self.TIME_TICKS_END_SEC
        return None

    # -------------------------------------------------------------------------
    # Apoptosis Functions
    # -------------------------------------------------------------------------

    def _cycle_apoptosis(self) -> VerediHealth:
        '''
        System is being cycled into apoptosis state from current state.
        Current state is still set in self._life_cycle.

        Does not shut down MediatorServer. That is saved for the APOCALYPSE.
        '''
        super()._cycle_apoptosis()
        self.health = VerediHealth.APOPTOSIS

        # Just return APOPTOSIS even if our health is different?
        return VerediHealth.APOPTOSIS

    def _apoptosis_msg_filter(self,
                              message: Message,
                              context: VerediContext) -> VerediHealth:
        '''
        Checks server->game pipe's message. Drops it if we don't care about it.
        '''
        return message.type not in self.MSG_TYPE_IGNORE_WHILE_DYING

    def _update_apoptosis(self) -> VerediHealth:
        '''
        Structured death phase. System should be responsive until apocalypse,
        so just check if MediatorServer is busy right now or not.
        '''
        # Say we can be done if we have nothing from Mediator to deal with
        # right now... Probably also want some flag or something from Mediator
        # to say they're idle-ish?
        #
        # TODO [2020-10-08]: Flag or something for MediatorServer /
        # ProcToSubComm&SubToProcComm to indicate idle/busy status.

        health = tick_health_init(SystemTick.APOPTOSIS)

        if self.server.has_data():
            # (Try to) Process messages, with our apoptosis ignore-messages
            # filter.
            self._get_external_messages(
                message_fn=self._apoptosis_msg_filter)
            health = health.update(VerediHealth.APOPTOSIS)

        if self.server._ut_has_data():
            if DebugFlag.SYSTEM_DEBUG in self.debug_flags:
                msg, ctx = self.server._ut_recv()
                self._log_debug("Server received UNIT TEST data during "
                                "apoptosis: {}",
                                msg,
                                context=ctx)
                # log.ultra_hyper_debug(
                #     msg,
                #     title=(f"{self.__class__.__name__}._update_apoptosis: "
                #            "server _test_ msg:"))
                # log.ultra_hyper_debug(
                #     ctx,
                #     title=((f"{self.__class__.__name__}._update_apoptosis: "
                #             "server _test_ ctx:"))

            health = health.update(VerediHealth.APOPTOSIS_FAILURE)

        # Otherwise update our health with the resultant helth, and return
        # that specific value.
        self._health = health
        return health

    # -------------------------------------------------------------------------
    # Apocalypse Functions
    # -------------------------------------------------------------------------

    def _apocalypse_done_check(self) -> Union[Literal[False], VerediHealth]:
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
            VerediHealth.APOCALYPSE_DONE,
            VerediHealth.FATAL)
        return healthy_exit

    def _cycle_apocalypse(self) -> VerediHealth:
        '''
        System is being cycled into apocalypse state from current state.
        Current state is still set in self._life_cycle.
        '''
        super()._cycle_apocalypse()
        # Use the non-blocking multiproc functions!

        # ------------------------------
        # Start our Graceful Death.
        # ------------------------------
        self._health = self._health.update(VerediHealth.APOCALYPSE)

        # Start the teardown... We'll wait on it during _update_apocalypse().
        multiproc.nonblocking_tear_down_start(self.server)

        return VerediHealth.APOCALYPSE

    def _update_apocalypse(self) -> VerediHealth:
        '''
        Structured death phase. We actually shut down our MediatorServer now.
        '''
        timed_out = self._manager.time.is_timed_out(
                None,
                self.timeout_desired(SystemTick.APOCALYPSE))

        # Set to failure state if over time.
        if self._manager.time.is_timed_out(
                None,
                self.timeout_desired(SystemTick.APOCALYPSE)):
            # Don't care about tear_down_end result; we'll check it with
            # exitcode_healthy().
            multiproc.nonblocking_tear_down_end(self.server)

            if exit_health == VerediHealth.FATAL:
                log.error("MediatorServer exit failure. "
                          f"Exitcode: {self.server.process.exitcode}")

            # Update with exitcode's health, and...
            exit_health = self.server.exitcode_healthy(
                VerediHealth.APOCALYPSE_DONE,
                VerediHealth.FATAL)

            # Update with our health (failed due to overtime), and return.
            # overtime_health = VerediHealth.FATAL

            # Technically, we're already overtime, so updating our health with
            # both exit_health (of whatever it is) and overtime_health (of
            # FATAL) makes sense. However, if we successfully exited just now,
            # that minor bit of overtime can be ignored. So just use
            # exit_health.
            self._health = self._health.update(exit_health)
            return self.health

        # Else we still have time to wait.
        multiproc.nonblocking_tear_down_wait(self.server,
                                             log_enter=True)
        done = self._apocalypse_done_check()
        if done is not False:
            # Update with done's health since we're done.
            self._health = self._health.update(done)
        else:
            # Update health with APOCALYPSE, since we're in progress.
            self._health = self._health.update(VerediHealth.APOCALYPSE)

        return self.health

    # -------------------------------------------------------------------------
    # The End Functions
    # -------------------------------------------------------------------------

    def _cycle_the_end(self) -> VerediHealth:
        '''
        System is being cycled into the_end state from current state.
        Current state is still set in self._life_cycle.
        '''
        super()._cycle_the_end()

        exit_health = self.server.exitcode_healthy(
            VerediHealth.THE_END,
            VerediHealth.UNHEALTHY)

        # FATAL from exitcode_healthy means it's not dead. So tear it down now.
        if exit_health == VerediHealth.FATAL:
            # Don't care about tear_down_end result; we'll check it with
            # exitcode_healthy().
            exit_tuple = multiproc.nonblocking_tear_down_end(self.server)

            # I'd like to wait to recheck the health, but it's THE_END
            # so no choice.
            exit_health = self.server.exitcode_healthy(
                VerediHealth.THE_END,
                VerediHealth.FATAL)
        elif exit_health == VerediHealth.UNHEALTHY:
            # Used UNHEALTHY as an indication that server did actually exited,
            # but exited poorly. FATAL is reserved for "still alive, actually".
            # Now that we know it's not alive, upgrade unhealthy to fatal.
            exit_health = VerediHealth.FATAL

        self._health = self._health.update(exit_health)
        return exit_health
