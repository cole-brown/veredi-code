# coding: utf-8

'''
A Testing System for our Test_From_Scratch test case.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    Optional, Set, Type, Union, Dict)
if TYPE_CHECKING:
    from veredi.base.context import VerediContext


from veredi.logger                      import log

from veredi.data                        import background
from veredi.data.config.registry        import register

from veredi.game import ecs
from veredi.game.event import EngineStopRequest


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

@register('veredi', 'zest', 'functional', 'system')
class TestSystem(ecs.base.System):

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def _define_vars(self):
        '''
        Instance variable definitions, type hinting, doc strings, etc.
        '''
        super()._define_vars()

        self._countdown: int = 100
        '''
        Number of TICKS_RUN we want to allow the engine to do.
        '''

        self._ticks_seen: Dict[ecs.SystemTick, int] = {}

    def _configure(self, context: 'VerediContext') -> None:
        '''
        Make our stuff from context/config data.
        '''
        super()._configure(context)
        self._ticks: ecs.SystemTick = (ecs.SystemTick.TICKS_START
                                       | ecs.SystemTick.TICKS_RUN
                                       | ecs.SystemTick.TICKS_END)

    @classmethod
    def dotted(klass: 'TestSystem') -> str:
        # klass._DOTTED magically provided by @register
        return klass._DOTTED

    # -------------------------------------------------------------------------
    # System Registration / Definition
    # -------------------------------------------------------------------------

    def priority(self) -> Union[ecs.SystemPriority, int]:
        '''
        Returns a SystemPriority (or int) for when, relative to other systems,
        this should run. Highest priority goes firstest.
        '''
        return ecs.SystemPriority.MEDIUM

    # -------------------------------------------------------------------------
    # Events
    # -------------------------------------------------------------------------

    # def _subscribe(self) -> ecs.VerediHealth:
    #     '''
    #     Subscribe to any life-long event subscriptions here. Can hold on to
    #     event_manager if need to sub/unsub more dynamically.
    #     '''
    #     health = super()._subscribe()
    #     self._manager.event.subscribe(AbilityRequest,
    #                                   self.event_ability_req)
    #
    #     return health.update(VerediHealth.HEALTHY)
    #
    # def event_ability_req(self, event: AbilityRequest) -> None:
    #     '''
    #     Ability check - please do the thing.
    #     '''
    #     # Doctor checkup.
    #     if not self._health_ok_event(event):
    #         return
    #
    #     entity, component = self._manager.get_with_log(
    #         f'{self.__class__.__name__}.command_ability',
    #         event.id,
    #         self._component_type,
    #         event=event)
    #     if not entity or not component:
    #         # Entity or component disappeared, and that's ok.
    #         return
    #
    #     result = self._query(event.id,
    #                          event.ability,
    #                          event.context)
    #
    #     # Have EventManager create and fire off event for whoever wants the
    #     # next step.
    #     next_event = AbilityResult(event, result)
    #     self._event_notify(next_event)

    # -------------------------------------------------------------------------
    # System Ticks
    # -------------------------------------------------------------------------

    @property
    def ticks_seen(self) -> Dict[ecs.SystemTick, int]:
        '''
        Returns our dictionary of tick type counters.
        '''
        return self._ticks_seen

    def _tick_increment(self,
                        tick: ecs.SystemTick) -> None:
        '''
        Count this tick in our ticks counter dictionary.
        '''
        counter = self._ticks_seen.setdefault(tick, 0)
        counter += 1
        self._ticks_seen[tick] = counter

    def update_tick(self,
                    tick: ecs.SystemTick) -> ecs.VerediHealth:
        '''
        Overwrite the generic tick function since we want all ticks.
        '''
        health = ecs.tick_health_init(tick)

        self._tick_increment(tick)

        # Once per TICKS_RUN cycle, count down towards stopping the engine.
        if tick is ecs.SystemTick.STANDARD:
            self._countdown -= 1
            # Only trigger event once. Want to know if it gets lost.
            if self._countdown == 0:
                # TODO: These when there is no entity?
                event_owner_id = -1
                event_type = -1
                # TODO: Make a SystemContext and (base)System._context() or
                # something so systems have something to start from?
                event_context = None

                # Ask the engine to stop.
                self._event_create(EngineStopRequest,
                                   event_owner_id,
                                   event_type,
                                   event_context)

        self.health = health
        return health
