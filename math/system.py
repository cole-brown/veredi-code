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
                    Set, Tuple)
from veredi.base.null import NullNoneOr
if TYPE_CHECKING:
    from veredi.base.context     import VerediContext
    from veredi.game.ecs.manager import EcsManager

from decimal import Decimal

# ---
# Code
# ---
from veredi.logs                        import log
from veredi.base.const                  import VerediHealth
from veredi.base                        import numbers
from veredi.data.config.registry        import register

# Game / ECS Stuff
from veredi.game.ecs.event              import EventManager, Event
from veredi.game.ecs.time               import TimeManager
from veredi.game.ecs.component          import ComponentManager
from veredi.game.ecs.entity             import EntityManager
from veredi.game.ecs.system             import SystemManager

from veredi.game.ecs.const              import (SystemTick,
                                                SystemPriority)
from veredi.game.ecs.base.identity      import EntityId

from veredi.game.ecs.base.system        import System

# Everything needed to participate in command registration.
from veredi.interface.input.command.reg import (CommandStatus,
                                                CommandExecutionError)
from veredi.interface.input.context     import InputContext
from veredi.math.parser                 import MathTree

# Maths
from .evaluator                         import Evaluator
from .exceptions                        import MathError
from .                                  import event as math_event

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

MathVarCanonicalize = NewType(
    'MathVarCanonicalize',
    Callable[[str], NullNoneOr[str]])

MathVarFill = NewType(
    'MathVarFill',
    Callable[[EntityId, str, Optional[InputContext]], VerediHealth])


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
    entity_id:    EntityId

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
             entry: MathEntry) -> None:
        self._queue.append(entry)

    def pop(self):
        return self._queue.pop()

    def __len__(self):
        return len(self._queue)

    def __str__(self):
        return f"MathQueue({self._queue})"

    def __repr__(self):
        return f"<MathQueue({self._queue})>"


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

    @classmethod
    def dotted(klass: 'MathSystem') -> str:
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
        # Math when everyone's done?
        return SystemPriority.LOW

    # -------------------------------------------------------------------------
    # Events
    # -------------------------------------------------------------------------

    # TODO: subscribe to cmd reg event? Subscribe to 'math me plz' event.

    # def _subscribe(self) -> VerediHealth:
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
    #     return VerediHealth.HEALTHY

    # def event_cmd_reg(self, event: CommandRegistrationBroadcast) -> None:
    #     '''
    #     Skill thingy requested to happen; please resolve.
    #     '''
    #     # Doctor checkup.
    #     if not self._health_ok_event(event):
    #         return

    #     skill_check = CommandRegisterReply(event,
    #                                        self.dotted(),
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
    #     if not self._healthy(self._manager.time.engine_tick_current):
    #         self._health_meter_event = self._health_log(
    #             self._health_meter_event,
    #             log.Level.WARNING,
    #             "HEALTH({}): Dropping event {} - our system health "
    #             "isn't good enough to process.",
    #             self.health, event,
    #             context=event.context)
    #         return

    #     entity, component = background.manager.meeting.get_with_log(
    #         f'{self.__class__.__name__}.event_skill_req'
    #         event.id,
    #         SkillComponent,
    #         event=event)
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

        eid = InputContext.source_id(context)
        if not eid:
            eid = result_event.id

        entry = MathEntry(input,
                          context,
                          eid,
                          canonicalize_fn,
                          fill_fn,
                          result_event)
        failed_on = self.resolve(entry)
        if failed_on:
            return CommandStatus.parsing(
                failed_on,
                f"Failed parsing '{failed_on}' into math expression.",
                f"Failed parsing '{failed_on}' into math expression.")
        return CommandStatus.successful(entry.context)

    def _resolve_var(self,
                     entry: MathEntry,
                     var:   MathTree,
                     canon: str) -> Tuple[bool, Optional[MathTree]]:
        '''
        Resolves this one variable in the whole MathTree.

        Returns: (success, replacement)
          replacement:
            - If failed when trying to replace var, returns var.
            - If finished (var resolved to a number), returns None.
            - Else returns MathTree of what var resolved to.
        '''

        # Fill in canonical string's value.
        value, milieu = entry.fill(entry.entity_id, canon, entry.context)

        if self._should_debug():
            self._log_debug(f"replace '{canon}' with "
                            "'{str(type(value))}({value})' and '{milieu}'")
            self._log_debug(f"'{value}' is {numbers.NumberTypesTuple}? "
                            "{isinstance(value, numbers.NumberTypesTuple)}")

        # Is that it, or do we need to keep going?
        if isinstance(value, numbers.NumberTypesTuple):
            var.set(value, milieu)
            return True, None

        else:
            # Parse value as MathTree, replace our node with it.
            mather = InputContext.math(entry.context)
            if not mather:
                msg = ("No MathParser found in context; "
                       "cannot process '{value}'.")
                raise self._log_exception(CommandExecutionError,
                                          msg,
                                          context=entry.context)

            if self._should_debug():
                self._log_debug(f"mather.parse(value='{value}', "
                                f"milieu='{milieu}'")

            replacement = mather.parse(value, milieu)

            if self._should_debug():
                self._log_debug("replacement: {}", replacement)

            if not replacement:
                # Return what we failed on.
                return False, value

            return True, replacement

    def resolve(self, entry: MathEntry) -> Optional[MathTree]:
        '''
        Resolve vars in this entry; place result back into correct queue.
        '''

        # Resolve each var.
        resolved = 0
        replace = []
        for var in entry.root.each_var():
            if self._should_debug():
                self._log_debug(f"      ----- working on var: {var} -----")
                self._log_debug(f"canonicalize_fn: var.name: {var.name}, "
                                f"var.milieu: {var.milieu}")
            # If the function can canonicalize this variable's name, we'll
            # assume it's the owner and have it fill it in.
            canon = entry.canonicalize(var.name, var.milieu)
            if not canon:
                continue

            success, replacement = self._resolve_var(entry, var, canon)
            if not success:
                # Return what we failed on.
                return replacement

            # if success and not replacement: Nothing to do.
            if success and replacement:
                # Replace when we're done iterating over tree.
                replace.append((var, replacement))

        # Replace resolved nodes in tree as needed.
        replaced = 0
        for existing, replacement in replace:
            if not entry.root.replace(existing, replacement):
                msg = ("Failed to replace a math tree node: {existing} "
                       "cannot replace with: {replacement}")
                raise self._log_exception(CommandExecutionError,
                                          msg,
                                          context=entry.context)
            replaced += 1

        if self._should_debug():
            self._log_debug("Resolved: {}", resolved)
            self._log_debug("Replaced: {}", replaced)
        if not resolved and not replaced:
            # Math has come to steady state... stick in final queue.
            self._finalize.push(entry)
            if self._should_debug():
                self._log_debug('Pushed to finalize. len: {}',
                                len(self._finalize))
        else:
            # Math is still wibbly-wobbly.
            self._recurse.push(entry)
            if self._should_debug():
                self._log_debug('Pushed to recurse. len: {}',
                                len(self._recurse))

        return None

    # -------------------------------------------------------------------------
    # Game Update Loop/Tick Functions
    # -------------------------------------------------------------------------

    def _update_pre(self) -> VerediHealth:
        '''
        SystemTick.PRE
        '''
        return self._update_any()

    def _update(self) -> VerediHealth:
        '''
        SystemTick.PRE
        '''
        return self._update_any()

    def _update_post(self) -> VerediHealth:
        '''
        SystemTick.PRE
        '''
        return self._update_any()

    def _update_any(self) -> VerediHealth:
        '''
        Generic tick function. We do the same thing every tick state we process
        so do it all here.
        '''
        # Doctor checkup.
        if not self._health_ok_tick(SystemTick.STANDARD):
            return self.health

        # TODO [2020-07-04]: Could have these do a max amount per tick.

        # Do however many we have queued up. Ignore requeues...
        for i in range(len(self._recurse)):
            entry = self._recurse.pop()
            failure = self.resolve(entry)
            if failure:
                if self._should_debug():
                    self._log_debug('recurse failure:', failure)
                # TODO [2020-07-05]: let someone known or something?
                # Send out result event as error somehow.
                self._log_error("TODO: let someone known or something? "
                                "failure: {}",
                                failure)
                continue

        # Do however many we have queued up.
        for i in range(len(self._finalize)):
            entry = self._finalize.pop()
            total = None
            try:
                total = Evaluator.eval(entry.root)
                if self._should_debug():
                    self._log_debug("Evaluated math tree to: {}. tree: \n{}",
                                    total, entry.root)
            except ValueError as eval_error:
                msg = "Failed to evaluate math tree."
                error = MathError(msg,
                                  context=entry.context,
                                  data={
                                      'root': entry.root,
                                  })
                raise self._log_exception(error,
                                          msg,
                                          context=entry.context
                                          ) from eval_error

            # Send out result as event. Finalize if a math type of event.
            if isinstance(entry.event, (math_event.MathEvent,
                                        math_event.MathOutputEvent)):
                entry.event.finalize(entry.root, total)
            self._event_notify(entry.event)

        if self._should_debug():
            self._log_debug('Updated.')
            self._log_debug('    self._recurse:  {}',
                            self._recurse)
            self._log_debug('    self._finalize: {}',
                            self._finalize)

        # Done for this tick.
        # TODO: Should time manager have current engine tick/life-cycle?
        return self._health_check(SystemTick.STANDARD)
