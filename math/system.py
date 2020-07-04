# coding: utf-8

'''
System for dealing with MathTrees, math-based commands, etc.

Handles:
  - MathTrees
  - Math-based commands
  - Other things probably.
'''


# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

# ---
# Typing
# ---
from typing import (TYPE_CHECKING,
                    Optional, Union, Type, NewType, NamedTuple, Callable,
                    Set, Iterable, Tuple)
from veredi.base.null import Null, Nullable, NullNoneOr
if TYPE_CHECKING:
    from veredi.base.context     import VerediContext
    from veredi.game.ecs.manager import EcsManager

from decimal import Decimal

# ---
# Code
# ---
from veredi.logger                  import log
from veredi.base.const              import VerediHealth
from veredi.data                    import background
from veredi.data.config.registry    import register
from veredi.data.codec.adapter      import definition

# Game / ECS Stuff
from veredi.game.ecs.event          import EventManager, Event
from veredi.game.ecs.time           import TimeManager
from veredi.game.ecs.component      import ComponentManager
from veredi.game.ecs.entity         import EntityManager
from veredi.game.ecs.system         import SystemManager

from veredi.game.ecs.const          import (SystemTick,
                                            SystemPriority)

from veredi.game.ecs.base.identity  import ComponentId
from veredi.game.ecs.base.system    import System
from veredi.game.ecs.base.component import Component

# Everything needed to participate in command registration.
from veredi.input.command.reg       import (CommandRegistrationBroadcast,
                                            CommandRegisterReply,
                                            CommandPermission,
                                            CommandArgType,
                                            CommandStatus,
                                            CommandExecutionError)
from veredi.math.parser             import MathTree
from veredi.input.context           import InputContext

# Maths
from .evaluator import Evaluator
from .exceptions import MathError
from . import event


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

MathVarCanonicalize = NewType(
    'MathVarCanonicalize',
    Callable[[str], NullNoneOr[str]])

MathVarFill = NewType(
    'MathVarFill',
    Callable[[str, Optional[InputContext]], VerediHealth])


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

class MathEntry(NamedTuple):
    '''
    A MathQueue item.
      - MathTree and its context.
      - Two functions:
        - canonicalize:
          - Should turn a string into a 'canonical' string if it is known to
            the system.
          - Should return None/Null if not.
        - fill:
          - Should fulfill a canonicalized string with a value (and optional
            milieu, if needed).
      - Event:
        - Should be filled out already - we don't replace 'root' so it can be
          put in there.
    '''
    # Inputs from InputSystem / User
    root:         MathTree
    context:      InputContext

    # Functions from command source system.
    canonicalize: MathVarCanonicalize
    fill:         MathVarFill

    # What to do with Result
    event:       Event


class MathQueue:
    '''
    A FIFO queue of MathEntries.
    '''

    def __init__(self) -> None:
        self._queue = []

    def push(self,
             root:         MathTree,
             context:      InputContext,
             canonicalize: Optional[MathVarCanonicalize] = None,
             fill:         Optional[MathVarFill]         = None) -> None:
        self._queue.add(MathEntry(root, context))

    def pop(self):
        return self._queue.pop()


@register('veredi', 'math', 'system')
class MathSystem(System):

    def _configure(self, context: 'VerediContext') -> None:
        '''
        Make our stuff from context/config data.
        '''
        self._recurse:  'MathQueue' = MathQueue()
        self._finalize: 'MathQueue' = MathQueue()

        # ---
        # Health Stuff
        # ---
        self._required_managers:    Optional[Set[Type[EcsManager]]] = {
            TimeManager,
            EventManager,
            SystemManager,
        }
        self._health_meter_update:  Optional['Decimal'] = None
        self._health_meter_event:   Optional['Decimal'] = None

        # ---
        # Ticking Stuff
        # ---
        # Process on three ticks to spread ourselves out a bit?
        self._ticks: SystemTick = (SystemTick.PRE
                                   | SystemTick.STANDARD
                                   | SystemTick.POST)

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
        # Math when everyone's done?
        return SystemPriority.LOW

    # -------------------------------------------------------------------------
    # Events
    # -------------------------------------------------------------------------

    # TODO: subscribe to cmd reg event? Subscribe to 'math me plz' event.

    # def subscribe(self, event_manager: EventManager) -> VerediHealth:
    #     '''
    #     Subscribe to any life-long event subscriptions here. Can hold on to
    #     event_manager if need to sub/unsub more dynamically.
    #     '''
    #     super().subscribe(event_manager)
    #     # MathSystem subs to:
    #     # - CommandRegistrationBroadcast
    #     # - SkillRequests
    #     self._manager.event.subscribe(CommandRegistrationBroadcast,
    #                                   self.event_cmd_reg)
    #     self._manager.event.subscribe(SkillRequest,
    #                                   self.event_skill_req)
    #     return self._health_check()

    # def event_cmd_reg(self, event: CommandRegistrationBroadcast) -> None:
    #     '''
    #     Skill thingy requested to happen; please resolve.
    #     '''
    #     # Doctor checkup.
    #     if not self._health_ok_event(event):
    #         return

    #     skill_check = CommandRegisterReply(event,
    #                                        self.dotted,
    #                                        'skill',
    #                                        CommandPermission.COMPONENT,
    #                                        self.command_skill,
    #                                        description='roll a skill check')
    #     skill_check.set_permission_components(SkillComponent)
    #     skill_check.add_arg('skill name', CommandArgType.VARIABLE)
    #     skill_check.add_arg('additional math', CommandArgType.MATH,
    #                         optional=True)

    #     self._event_notify(skill_check)

    # def event_skill_req(self, event: SkillRequest) -> None:
    #     '''
    #     Skill thingy requested to happen; please resolve.
    #     '''
    #     # Doctor checkup.
    #     if not self._healthy():
    #         self._health_meter_event = self._health_log(
    #             self._health_meter_event,
    #             log.Level.WARNING,
    #             "HEALTH({}): Dropping event {} - our system health "
    #             "isn't good enough to process.",
    #             self.health, event,
    #             context=event.context)
    #         return

    #     entity, component = self._log_get_both(event.id,
    #                                            SkillComponent,
    #                                            event=event)
    #     if not entity or not component:
    #         # Entity or component disappeared, and that's ok.
    #         return

    #     amount = component.total(event.skill)
    #     log.debug("Event {} - {} total is: {}",
    #               event, event.skill, amount,
    #               context=event.context)

    #     # Have EventManager create and fire off event for whoever wants the
    #     # next step.
    #     if component.id != ComponentId.INVALID:
    #         next_event = SkillResult(event.id, event.type, event.context,
    #                                  component_id=component.id,
    #                                  skill=event.skill, amount=amount)
    #         self._event_notify(next_event)

    # -------------------------------------------------------------------------
    # Math-Language Command Helper
    # -------------------------------------------------------------------------

    def command(self,
                input: MathTree,
                canonicalize_fn: MathVarCanonicalize,
                fill_fn: MathVarFill,
                result_event: Event,
                context: Optional[InputContext] = None
                ) -> CommandStatus:
        '''
        Command helper for math-based commands. MathSystem will call invokees,
        check returns, do it all over again if the math is recursive...

        Once mathing is done, result_event will be publish as-is. So if you
        want the result, you should put `input` into your event. It is filled
        in in-place.
          - If the event is a MathEvent or child class, we will fill in its
            math tree and result total for you.
        '''
        # Doctor checkup.
        if not self._health_ok_msg("Command ignored due to bad health.",
                                   context=context):
            return CommandStatus.system_health(context)

        # Get skill totals for each var that's a skill name.
        resolved = 0
        replace = []
        for var in input.each_var():
            # If the function can canonicalize this variable's name, we'll
            # assume it's the owner and have it fill it in.
            canon = canonicalize_fn(var.name)
            if not canon:
                continue

            value, milieu = fill_fn(canon, context)
            if isinstance(value, event.MathResultTuple):
                var.set(value, milieu)
                resolved += 1
            else:
                # Parse value as MathTree, replace our node with it.
                mather = InputContext.math(context)
                if not mather:
                    error = ("No MathParser found in context; "
                             "cannot process '{value}'.")
                    raise log.exception(AttributeError(error),
                                        CommandExecutionError,
                                        None,
                                        context=context)
                replacement = mather.parse(value, milieu)
                if not replacement:
                    return CommandStatus.parsing(
                        value,
                        f"Failed parsing '{value}' into math expression.",
                        f"Failed parsing '{value}' into math expression.")

                # Replace when we're done iterating over tree.
                replace.append((var, replacement))

        replaced = 0
        for existing, replacement in replace:
            if not input.replace(existing, replacement):
                error = ("Failed to replace a math tree node: {existing} "
                         "cannot replace with: {replacement}")
                raise log.exception(None,
                                    CommandExecutionError,
                                    error,
                                    context=context)
            replaced += 1

        if not resolved and not replaced:
            # Math has come to steady state... stick in final queue.
            self._finalize.push(input, context)
        else:
            # Math is still wibbly-wobbly.
            self._recurse.push(input,
                               context,
                               canonicalize_fn,
                               fill_fn)

        return CommandStatus.successful(context)

    # -------------------------------------------------------------------------
    # Game Update Loop/Tick Functions
    # -------------------------------------------------------------------------

    def _update(self,
                tick:          SystemTick,
                time_mgr:      TimeManager,
                component_mgr: ComponentManager,
                entity_mgr:    EntityManager) -> VerediHealth:
        '''
        Generic tick function. We do the same thing every tick state we process
        so do it all here.
        '''
        # Doctor checkup.
        if not self._health_ok_tick(tick):
            return self.health

        # TODO [2020-07-04]: Could have these do a max amount per tick.

        # Do however many we have queued up. Ignore requeues...
        for i in range(len(self._recurse)):
            entry = self._recurse.pop()
            status = self.command(entry.math,
                                  entry.canonicalize,
                                  entry.fill,
                                  entry.context)
            if not status:
                log.warning("TODO: let commander known or something?")
                continue

        # Do however many we have queued up.
        for i in range(len(self._finalize)):
            entry = self._finalize.pop()
            total = None
            try:
                total = Evaluator.eval(entry.root)
                log.debug("Evaluated math tree to: {}. tree: \n{}",
                          total, entry.root)
            except ValueError as error:
                raise log.exception(error,
                                    MathError,
                                    context=entry.context)

            # Send out result as event.
            if isinstance(entry.event, event.MathEvent):
                entry.event.finalize(entry.root, total)
            self._event_notify(entry.event)

        # Done for this tick.
        return self._health_check()
