# coding: utf-8

'''
Output System for Veredi.

Handles:
  - Output Events like
    - Command output
    - Roll output
    - Chat output
    - Literally all output from game to users.
  - Other things probably.

Alot of Outputs.
'''


# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

# ---
# Typing
# ---
from typing import (TYPE_CHECKING,
                    Optional, Union, Type, Callable, NamedTuple, Set, List)
if TYPE_CHECKING:
    from decimal                   import Decimal

    from veredi.base.context       import VerediContext
    from veredi.game.ecs.component import ComponentManager
    from veredi.game.ecs.entity    import EntityManager
    from veredi.game.ecs.manager   import EcsManager


# ---
# Code
# ---
from veredi.data                         import background

from veredi.logger                       import log
from veredi.base.const                   import VerediHealth
from veredi.data.config.registry         import register
from veredi.data.serdes.string           import StringSerdes

# Game / ECS Stuff
from veredi.game.ecs.event               import EventManager
from veredi.game.ecs.time                import TimeManager

from veredi.game.ecs.const               import (SystemTick,
                                                 SystemPriority)

from veredi.game.ecs.base.system         import System
from veredi.game.ecs.base.component      import Component
from veredi.game.data.identity.component import IdentityComponent

# Input-Related Stuff?
# from ..input.context                     import InputContext
# from ..input                             import sanitize
# from ..input.parse                       import Parcel
# from ..input.command.commander           import Commander
# from ..input.history.history             import Historian
# from ..input.event                       import CommandInputEvent
# from ..input.component                   import InputComponent

# Output-Related Stuff
from .event                              import OutputEvent, OutputType


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

class SendEntry(NamedTuple):
    '''
    Packages up what to send and to whom.
    '''
    payload:      str
    payload_type: OutputType
    target_type:  OutputType


@register('veredi', 'interface', 'output', 'system')
class OutputSystem(System):

    def _configure(self, context: 'VerediContext') -> None:
        '''
        Make our stuff from context/config data.
        '''
        self._ut_recv_fn = None

        self._event_queue: List[OutputEvent] = []
        '''
        Output queue we work on every tick. OutputEvents just get pushed into
        here when we receive them.
        '''

        self._event_retry: List[OutputEvent] = []
        '''
        Output queue for OutputEvents that turned out to not quite be ready
        yet. Will try again next tick.
        '''

        self._send_queue: List['SendEntry'] = []
        '''
        Output queue we work on every tick. Final output gets pushed to users
        from here.
        '''

        self._component_type: Type[Component] = None
        '''Don't have a component type for output right now.'''

        # ---
        # Health Stuff
        # ---
        self._required_managers:   Optional[Set[Type['EcsManager']]] = {
            TimeManager,
            EventManager,
        }
        self._health_meter_update: Optional['Decimal'] = None
        self._health_meter_event:  Optional['Decimal'] = None

        # ---
        # Ticking Stuff
        # ---
        self._components: Optional[Set[Type[Component]]] = None

        # Just POST tick? For catching any output that became ready in the
        # STANDARD tick?
        self._ticks: SystemTick = SystemTick.POST

        # ---
        # Config Stuff
        # ---
        self._codec = None
        self._serdes = StringSerdes()

        config = background.config.config
        if config:
            self._codec = config.make(None,
                                      'server',
                                      'output',
                                      'codec')

        # ---
        # Background Context Stuff
        # ---
        # Create our background context now that we have enough info.
        bg_data, bg_owner = self._background
        background.output.set(self.dotted,
                              bg_data,
                              bg_owner)

    @property
    def _background(self):
        '''
        Get background data for background.output.set().
        '''
        codec_data, _ = self._codec.background
        serdes_data, _ = self._serdes.background
        self._bg = {
            'dotted': self.dotted,
            'codec': codec_data,
            'serdes': serdes_data,
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
        # LOW so everything can happen before we do our output for the tick?
        return SystemPriority.LOW

    # -------------------------------------------------------------------------
    # Events
    # -------------------------------------------------------------------------

    def subscribe(self, event_manager: EventManager) -> VerediHealth:
        '''
        Subscribe to any life-long event subscriptions here. Can hold on to
        event_manager if need to sub/unsub more dynamically.
        '''
        super().subscribe(event_manager)

        # OutputSystem subs to:
        # - OutputEvents
        self._manager.event.subscribe(OutputEvent,
                                      self.event_output)

        return self._health_check()

    def event_output(self, event: OutputEvent) -> None:
        '''
        Output thingy requested to happen; please resolve.
        '''
        # Doctor checkup.
        if not self._health_ok_event(event):
            return

        self._event_queue.append(event)

    # -------------------------------------------------------------------------
    # Game Update Loop/Tick Functions
    # -------------------------------------------------------------------------

    def _update_post(self,
                     time_mgr:      TimeManager,
                     component_mgr: 'ComponentManager',
                     entity_mgr:    'EntityManager') -> VerediHealth:
        '''
        SystemTick.POST tick function.
        '''
        # Doctor checkup.
        if not self._health_ok_tick(SystemTick.POST):
            return self.health

        # ---
        # Process our Events
        # ---
        for output in self._event_queue:
            if self._process_output(output):
                continue
            # Failed... retry?
            self._event_retry.append(output)

        # Done with our outputting. Clear out the output queue and then swap it
        # and the retry queue out in preparation of the next tick.
        self._event_queue.clear()
        (self._event_queue,
         self._event_retry) = (self._event_retry,
                               self._event_queue)

        # ---
        # Send our Outputs
        # ---
        for output in self._send_queue:
            self._send_output(output)

        # Done with our sending. Clear out the send in preparation of the next
        # tick.
        self._send_queue.clear()

        return self._health_check()

    # -------------------------------------------------------------------------
    # Output Processing
    # -------------------------------------------------------------------------

    def _process_output(self, output: OutputEvent) -> bool:
        '''
        Prepare output event, send to proper users with proper data (e.g.
        GM-only data), etc.

        Returns bool for success in processing/sending output.
        '''
        # TODO [2020-07-06]: Do we save the output to the historian?
        # I think so. We need the result so we can undo the thing.
        # TODO: Send to historian.
        log.warning("TODO: send to historian?")

        # Use codec to encode output for transmit.
        # TODO: Need...
        #   - Title
        #   - Names Dict
        # TODO: Check output flags.
        #   - Encode differently for GM, players?
        #   - Encode differently for owner player, other players?
        encoded_for = OutputType.BROADCAST
        encoded = self._codec.encode(output, output.context)
        if self._should_debug():
            self._log(log.Level.DEBUG,
                      "encoded output: {}",
                      encoded)
        serialized = self._serdes.serialize(encoded, output.context)
        if self._should_debug():
            self._log(log.Level.DEBUG,
                      "serialized output: {}",
                      serialized)

        # Queue up output to be sent... wherever it should go.
        send_to = OutputType.BROADCAST
        entry = SendEntry(serialized, encoded_for, send_to)
        self._send_queue.append(entry)

        # And... Done? Nothing more to do now at this point?
        return True

    # -------------------------------------------------------------------------
    # Output Sending
    # -------------------------------------------------------------------------

    def _send_output(self,
                     output: 'SendEntry',
                     skip:   Optional[OutputType] = None) -> None:
        '''
        Sends `output` to necessary users.

        Checks, adds to `skip` flags; returns updated skip flag mask.

        E.g. Adds 'GM' flag to `skip`

        E.g. if broadcasting, can skip GM user in broadcast if already sent to
        GM at GM encoding in previous step.
        '''
        if self._ut_recv_fn:
            self._ut_recv_fn(output)

        if not skip:
            skip = OutputType.INVALID

        if (output.target_type.has(OutputType.GM)
                and output.payload_type.has(OutputType.GM)
                and not skip.has(OutputType.GM)):
            self._send_gm(output)
            skip = skip.set(OutputType.GM)

        if (output.target_type.any(OutputType.USER)
                and output.payload_type.has(OutputType.USER)
                and not skip.has(OutputType.USER)):
            self._send_user(output)
            skip = skip.set(OutputType.USER)

        if (output.target_type.any(OutputType.BROADCAST)
                and output.payload_type.has(OutputType.BROADCAST)
                and not skip.has(OutputType.BROADCAST)):
            self._send_broadcast(output)
            skip = skip.set(OutputType.BROADCAST)

        return skip

    def _send_gm(self, output: 'SendEntry') -> None:
        '''
        TODO: Actually do this...
        '''
        pass

    def _send_user(self, output: 'SendEntry') -> None:
        '''
        TODO: Actually do this...
        '''
        pass

    def _send_broadcast(self, output: 'SendEntry') -> None:
        '''
        TODO: Actually do this...
        '''
        pass

    # -------------------------------------------------------------------------
    # Unit Testing
    # -------------------------------------------------------------------------

    def _unit_test(self,
                   receiver_fn: Callable[['SendEntry'], None] = None) -> None:
        '''
        Set or unset 'receiver' to send to for unit testing.
        '''
        self._ut_recv_fn = receiver_fn
