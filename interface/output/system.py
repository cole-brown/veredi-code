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
                    Optional, Union, Type, Callable, Set, List)
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

from veredi.security                     import abac
from veredi.security.context             import SecurityContext

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
from .event                              import OutputEvent, OutputTarget
from .envelope                           import Envelope, Message, BasePayload


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

UT_OutRxCallback = Callable[['Envelope', Optional[OutputTarget]], None]
'''
Callback for unit tests that want to side-channel receive outputs.
Parameters will be the Envelope used for sending and all OutputTargets sent to.
'''


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

@register('veredi', 'interface', 'output', 'system')
class OutputSystem(System):

    _MAX_PER_TICK = 50

    def _define_vars(self):
        '''
        Instance variable definitions, type hinting, doc strings, etc.
        '''
        super()._define_vars()

        self._event_queue: List[OutputEvent] = []
        '''
        Output queue we work on every tick. OutputEvents just get pushed into
        here when we receive them.
        '''

        self._send_queue: List['Envelope'] = []
        '''
        Output queue we work on every tick. Final output gets pushed to users
        from here.
        '''

        self._component_type: Type[Component] = None
        '''Don't have a component type for output right now.'''

        # ------------------------------
        # TODO: DELETE THESE
        # ------------------------------
        # ---
        # Config Stuff
        # ---
        self._codec: Optional[Codec] = None
        '''
        Optional Coder/Decoder for messages & envelopes. If None, skips codec
        step.
        '''

        self._serdes: StringSerdes = StringSerdes()
        '''
        Serializer/deserializer for messages & envelopes.
        '''
        # ------------------------------
        # /TODO: DELETE THESE
        # ------------------------------

        # ---
        # Security: Access Control
        # ---
        self._pdp: 'abac.PolicyDecisionPoint' = None

        # ---
        # Unit Test Stuff
        # ---
        self._ut_recv_fn: UT_OutRxCallback = None
        '''
        Will also call this function, if it is not None, when sending out our
        envelopes.
        '''

    def _configure(self, context: 'VerediContext') -> None:
        '''
        Make our stuff from context/config data.
        '''

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
        config = background.config.config
        if config:
            self._codec = config.make(None,
                                      'server',
                                      'output',
                                      'codec')

        # ---
        # Security: Access Control
        # ---
        # TODO: get an actual policy from config
        self._pdp = abac.PolicyDecisionPoint()

        # ---
        # Background Context Stuff
        # ---
        # Create our background context now that we have enough info.
        bg_data, bg_owner = self._background
        background.output.set(self.dotted,
                              bg_data,
                              bg_owner)

        # ---
        # Unit Test Stuff
        # ---
        # Always start this off as unset. Will get set via self._unit_test()
        self._ut_recv_fn = None

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

    def _subscribe(self) -> VerediHealth:
        '''
        Subscribe to any life-long event subscriptions here. Can hold on to
        event_manager if need to sub/unsub more dynamically.
        '''
        # OutputSystem subs to:
        # - OutputEvents
        self._manager.event.subscribe(OutputEvent,
                                      self.event_output)

        return VerediHealth.HEALTHY

    def event_output(self, event: OutputEvent) -> None:
        '''
        Output thingy requested to happen; please resolve.
        '''
        # Doctor checkup.
        if not self._health_ok_event(event):
            # Bad health - already said we're dropping the event.
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
        remaining = self._MAX_PER_TICK
        retry = []
        for event in self._event_queue:
            # If we've done our max this tick, cancel out of checking the rest.
            # _event_queue is a queue, so this'll get to the proper 'next'
            # message next tick.
            remaining -= 1
            if remaining < 0:
                break

            # Try to process and send this event.
            if self._process_event(event):
                continue

            # Couldn't send this tick... next tick?
            retry.append(event)

        # ---
        # Prep Queues for Next Go.
        # ---

        # Done with our event processing. Get ready for next time by adding all
        # the events we tried but still need to retry back to the end of the
        # queue.
        self._event_queue.extend(retry)

        # ---
        # Send our Events
        # ---
        for event in self._send_queue:
            self._send_event(event)

        # Done with our sending. Clear out the send in preparation of the next
        # tick.
        self._send_queue.clear()

        return self._health_check(SystemTick.POST)

    # -------------------------------------------------------------------------
    # Output Processing
    # -------------------------------------------------------------------------

    def _process_event(self, event: OutputEvent) -> bool:
        '''
        Prepare output event, send to proper users with proper data (e.g.
        GM-only data), etc.

        Returns bool for success in processing/sending output.
        '''

        # TODO [2020-07-06]: Do we save the event to the historian?
        # I think so. We need the result so we can undo the thing.
        # TODO: Send to historian.
        self._log.warning("TODO: send to historian: event?")

        # ---
        # Optional: Codec
        # ---
        # Use codec to encode event for transmit, if we have one.
        encoded = None
        if self._codec:
            # TODO: Do we need...
            #   - Title
            #   - Names Dict
            # Or do we keep clients up to date with display strings in some
            # other way? title/names every message seems redundant/wasteful.

            # TODO: Check event flags.
            #   - Encode differently for GM, players?
            #   - Encode differently for owner player, other players?
            #
            # For now, just encode the same way for everyone.
            encoded = self._codec.encode(event, event.context)
            if self._should_debug():
                self._log.debug("encoded output: {}",
                                encoded)

        else:
            encoded = event.output
            if self._should_debug():
                # No encoder - just use the raw output.
                self._log.debug("No codec. Leaving output as-is: {}",
                                encoded)

        # TODO: optional or not?
        # ---
        # Optional?: Serialize output
        # ---
        # Use serializer on our output, if we have one.
        serialized = None
        if self._serdes:
            serialized = self._serdes.serialize(encoded, event.context)
            if self._should_debug():
                self._log.debug("serialized output: {}",
                                serialized)

        else:
            # Stick with output, assume it's serialized enough for whoever is
            # receiving this.
            serialized = encoded
            if self._should_debug():
                # No encoder - just use the raw output.
                self._log.debug("No serdes. Leaving output as-is: {}",
                                encoded)

        # Queue up output to be sent... wherever it should go.
        send_to = event.output_target
        eid = event.id
        entry = Envelope(send_to, eid, serialized)
        self._send_queue.append(entry)

        # And... Done? Nothing more to do now at this point?
        return True

    # -------------------------------------------------------------------------
    # Output Sending
    # -------------------------------------------------------------------------

    def _send_envelope(self,
                       envelope: 'Envelope') -> OutputTarget:
        '''
        Take the `envelope`, build a payload and then message based on
        the desired recipients, and then push an event for that message.

        Should only send to each intended recipient once. For example, a
        message intended for GM and broadcasting would be:
          1) Send output for GM; this notes that 'GM' recipient was sent to.

          2) User wasn't a target in this example, so it is ignored.

          3) Send output for broadcast; broadcast will knows it can skip over
             the GM (but not the User) while broadcasting since we gave the GM
             at least as much information as the broadcast receivers will get.

        Returns what recipients were sent to. Will probably be (should be)
        equal to self.recipients?
        '''
        # ---
        # Create address info.
        # ---
        # This is the point that the envelope gets its recipients validated.
        # It returns the new, validated recipients.
        allowed_recipients = self._address_envelope(envelope)

        todo make GameToMediatorEvent
        todo notify event

        # ---
        # Send to Unit Test if callback exists.
        # ---
        if self._ut_recv_fn:
            self._ut_recv_fn(envelope, sent_to)

        return sent_to

    def _address_envelope(self,
                          envelope: 'Envelope',
                          context:  'SecurityContext') -> None:
        '''
        Set address info for all intended recipients of this envelope.
        '''
        addressed_to = OutputTarget.INVALID

        # ---
        # Address to GM?
        # ---
        if envelope.intended_recipients.has(OutputTarget.GM):
            # We want to send to GM. Can we?
            if envelope.payload_type.has(OutputTarget.GM):
                self._address_to(envelope,
                                 OutputTarget.GM,
                                 abac.Subject.GM)
                addressed_to = addressed_to.set(OutputTarget.GM)
            else:
                self._log.error("Envelope recipient mismatch! The envelope "
                                "has 'GM' in intended_recipients "
                                f"({envelope.intended_recipients}), but not "
                                f"in payload_type ({envelope.payload_type}). "
                                "Ignoring this recipient level.")

        # ---
        # Address to owning/controlling User?
        # ---
        if envelope.intended_recipients.has(OutputTarget.USER):
            # We want to send to USER. Can we?
            if envelope.payload_type.has(OutputTarget.USER):
                self._address_to(envelope,
                                 OutputTarget.USER,
                                 abac.Subject.USER)
                addressed_to = addressed_to.set(OutputTarget.USER)
            else:
                self._log.error("Envelope recipient mismatch! The envelope "
                                "has 'USER' in intended_recipients "
                                f"({envelope.intended_recipients}), but not "
                                f"in payload_type ({envelope.payload_type}). "
                                "Ignoring this recipient level.")

        # ---
        # Broadcast to everyone connected?
        # ---
        if envelope.intended_recipients.has(OutputTarget.BROADCAST):
            # We want to send to BROADCAST. Can we?
            if envelope.payload_type.has(OutputTarget.BROADCAST):
                self._address_to(envelope,
                                 OutputTarget.BROADCAST,
                                 abac.Subject.BROADCAST)
                addressed_to = addressed_to.set(OutputTarget.BROADCAST)
            else:
                self._log.error("Envelope recipient mismatch! The envelope "
                                "has 'BROADCAST' in intended_recipients "
                                f"({envelope.intended_recipients}), but not "
                                f"in payload_type ({envelope.payload_type}). "
                                "Ignoring this recipient level.")

        return addressed_to

    def _address_to(self,
                    envelope:     'Envelope',
                    recipient:    OutputTarget,
                    access_level: abac.Subject) -> None:
        '''
        Add `recipient` to envelope's addressees as an
        `attribute-subject`-level receiver.
        '''
        if not self._pdp.allowed(envelope.context):
            abac.log.debug(f"Cannot address envelope to '{recipient}' "
                           f"at '{access_level}': "
                           "Security has denied the action.")
            return

        # ---
        # Get the actual "addresses" - user id/key.
        # ---
        todo -

        # ---
        # Address envelope to the recipient.
        # ---
        envelope.set_address(recipient,
                             access_level,
                             entity_id,
                             user_id,
                             user_key)

    # -------------------------------------------------------------------------
    # Unit Testing
    # -------------------------------------------------------------------------

    def _unit_test(self,
                   receiver_fn: UT_OutRxCallback = None) -> None:
        '''
        Set or unset 'receiver' to send to for unit testing.
        '''
        self._ut_recv_fn = receiver_fn
