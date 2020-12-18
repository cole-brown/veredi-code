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
from .event                              import OutputEvent, Recipient
from .envelope                           import Envelope, Message, BasePayload
from ..mediator.event                    import GameToMediatorEvent


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

UT_OutRxCallback = Callable[['Envelope', Optional[Recipient]], None]
'''
Callback for unit tests that want to side-channel receive outputs.
Parameters will be the Envelope used for sending and all Recipients sent to.
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
        # Just POST tick? For catching any output that became ready in the
        # STANDARD tick?
        self._ticks: SystemTick = SystemTick.POST

        # ---
        # Config Stuff
        # ---
        # config = background.config.config
        # if config:
        #     # Stuff from config.

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
        background.output.set(self.dotted(),
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
        self._bg = {
            'dotted': self.dotted(),
        }
        return self._bg, background.Ownership.SHARE

    @classmethod
    def dotted(klass: 'OutputSystem') -> str:
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

    def _update_post(self) -> VerediHealth:
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
        # Send our Envelopes out.
        # ---
        for envelope in self._send_queue:
            self._send_envelope(envelope)

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
        # Queue up output to be sent... wherever it should go.
        entry = Envelope(event)
        self._send_queue.append(entry)

        # TODO [2020-07-06]: Do we save the event to the historian?
        # I think so. We need the result so we can undo the thing.
        # TODO: Send to historian.
        self._log_warning("TODO: send {} to historian: OutputEvent? Envelope? "
                          "Wait for GameToMediatorEvent?",
                          event.serial_id)

        # And... Done? Nothing more to do now at this point?
        return True

    # -------------------------------------------------------------------------
    # Output Sending
    # -------------------------------------------------------------------------

    def _send_envelope(self,
                       envelope: 'Envelope') -> Recipient:
        '''
        Take the `envelope`, build a GameToMediatorEvent, and send it to the
        EventManager.

        Returns what recipients from the desired were validated. Will probably
        be (should be) equal to the desired recipients?
        '''
        # ---
        # Create address info.
        # ---
        # This is the point that the envelope gets its recipients validated.
        # It returns the new, validated recipients.
        allowed_recipients = self._address_envelope(envelope)

        # Create the event and notify our EventManager.
        event = GameToMediatorEvent(envelope)
        self._event_notify(event)

        # ---
        # Send to Unit Test if callback exists.
        # ---
        if self._ut_recv_fn:
            self._ut_recv_fn(envelope, allowed_recipients)

        return allowed_recipients

    def _address_envelope(self,
                          envelope: 'Envelope'
                          # TODO: SecurityContext?
                          ) -> Recipient:
        '''
        Set address info for all intended recipients of this envelope.

        Returns allowed recipients.
        '''
        addressed_to = Recipient.INVALID

        # ---
        # Address to GM?
        # ---
        if envelope.desired_recipients.has(Recipient.GM):
            # We want to send to GM. Can we?
            recipient = self._address_to(envelope,
                                         Recipient.GM,
                                         abac.Subject.GM)
            if recipient is Recipient.INVALID:
                self._log_error("Envelope recipient mismatch! The envelope "
                                "has 'GM' in desired_recipients "
                                f"({envelope.desired_recipients}), but "
                                "failed to address itself to them. "
                                "Ignoring this recipient level.")
            else:
                addressed_to = addressed_to.set(recipient)

        # ---
        # Address to owning/controlling User?
        # ---
        if envelope.desired_recipients.has(Recipient.USER):
            # We want to send to USER. Can we?
            recipient = self._address_to(envelope,
                                         Recipient.USER,
                                         abac.Subject.USER)
            if recipient is Recipient.INVALID:
                self._log_error("Envelope recipient mismatch! The envelope "
                                "has 'USER' in desired_recipients "
                                f"({envelope.desired_recipients}), but "
                                "failed to address itself to them. "
                                "Ignoring this recipient level.")
            else:
                addressed_to = addressed_to.set(recipient)

        # ---
        # Broadcast to everyone connected?
        # ---
        if envelope.desired_recipients.has(Recipient.BROADCAST):
            # We want to send to BROADCAST. Can we?
            recipient = self._address_to(envelope,
                                         Recipient.BROADCAST,
                                         abac.Subject.BROADCAST)
            if recipient is Recipient.INVALID:
                self._log_error("Envelope recipient mismatch! The envelope "
                                "has 'BROADCAST' in desired_recipients "
                                f"({envelope.desired_recipients}), but "
                                "failed to address itself to them. "
                                "Ignoring this recipient level.")
            else:
                addressed_to = addressed_to.set(recipient)

        envelope.valid_recipients = addressed_to
        return addressed_to

    def _address_to(self,
                    envelope:         'Envelope',
                    recipient:        Recipient,
                    security_subject: abac.Subject) -> Recipient:
        '''
        Add `recipient` to envelope's addressees as an
        `attribute-subject`-level receiver.

        Returns "allowed recipient", which is:
          - `recipient` on success.
          - Recipient.INVALID on failure.
        '''
        if not self._pdp.allowed(envelope.context):
            self._log_security(f"Cannot address envelope to '{recipient}' "
                               f"at '{security_subject}': "
                               "Security has denied the action.")
            # Recipient was not allowed by security - failure return.
            return Recipient.INVALID

        # ---
        # Get the actual "addresses" - user id/key.
        # ---
        users = None
        if recipient is Recipient.USER:
            # User/'owner' has their id in the event.
            users = background.users.connected(envelope.source_id)

        elif recipient is Recipient.GM:
            # Get all GMs for sending.
            users = background.users.gm(None)
            # TODO: presumably, in multi-gm games, only one GM should get
            # some/most/all 'GM' output... But I'm not sure how/where/why/etc
            # to demark it as such yet.

        elif recipient is Recipient.BROADCAST:
            # Get all connected users for sending.
            users = background.users.connected(None)

        if not users:
            self._log_debug(
                "No user(s) found for recipient {}, access {}. Ignoring.",
                recipient, security_subject)
            # Recipient was not found, which we'll treat as effectively a
            # failure/disallowed.
            return Recipient.INVALID

        # ---
        # Address envelope to the recipient.
        # ---
        envelope.set_address(recipient,
                             security_subject,
                             users)
        # Recipient was allowed, so return it.
        return recipient

    # -------------------------------------------------------------------------
    # Unit Testing
    # -------------------------------------------------------------------------

    def _unit_test(self,
                   receiver_fn: UT_OutRxCallback = None) -> None:
        '''
        Set or unset 'receiver' to send to for unit testing.
        '''
        self._ut_recv_fn = receiver_fn
