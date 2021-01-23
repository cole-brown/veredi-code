# coding: utf-8

'''
Component Manager. Manages life cycle of components, which should generally
follow the life cycle of their entity.

Do not hold onto Entities, Components, etc. They /can/ be destroyed at any
time, leaving you holding a dead object. Only keep the EntityId or ComponentId,
then ask its manager. If the manager returns None, the Entity/Component does
not exist anymore.

Inspired by:
  - Entity Component System design pattern
  - personal pain and suffering
  - mecs:
      https://github.com/patrick-finke/mecs
  - EntityComponentSystem:
      https://github.com/tobias-stein/EntityComponentSystem
'''


# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (TYPE_CHECKING,
                    Optional, Union, Type, Any, NewType,
                    Iterable, Set, List, Dict)
from veredi.base.null import NullNoneOr, Nullable, Null
if TYPE_CHECKING:
    from .time import TimeManager
    from veredi.base.identity import MonotonicIdGenerator


from veredi.logger             import log
from veredi.base.const         import VerediHealth
from veredi.base.context       import VerediContext
from veredi.data.config.config import Configuration
from veredi.data               import background
from veredi.debug.const        import DebugFlag

from .base.exceptions          import EcsComponentError
from .base.identity            import ComponentId
from .base.component           import (Component,
                                       ComponentLifeCycle)
from .event                    import (EcsManagerWithEvents,
                                       EventManager,
                                       Event)


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

CompOrNull = NewType('CompOrNull', Union[Component, Null])


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

class ComponentEvent(Event):
    ...


class ComponentLifeEvent(Event):
    pass


class ComponentManager(EcsManagerWithEvents):
    '''
    Manages the life cycles of components.

    Uses the Null Pattern object (veredi.base.null.Null) for components it
    doesn't have so you can safely code, say:
        for jeff_ent in all_jeff_entities:
            name = jeff_ent.get(NameComponent).name or fallback_value
            result = jeff_ent.get(ComplicatedComp).do_a_complicated_thing()
            if not result.success:
                self._log_info(...)
            ...

    The entities and components should be either: real or Null(), and so you'll
    get either real returns or Null(). So no need to do all this:
        for jeff_ent in all_jeff_entities:
            if not jeff_ent:
                continue
            name_comp = jeff_ent.get(NameComponent)
            if name_comp:
                name = name_comp.name
            else:
                name = fallback_value
            comp_comp = jeff_ent.get(ComplicatedComp)
            if comp_comp:
                result = comp_comp.do_a_complicated_thing()
                if not result or not result.success:
                    self._log_info(...)
                else:
                    ...
            else:
                ...
            ...
    '''

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def _define_vars(self) -> None:
        super()._define_vars()

        self._component_id:    'MonotonicIdGenerator' = ComponentId.generator()
        '''Our ID Generator for our components.'''

        self._component_create:  Set[ComponentId]     = set()
        '''Set of components to be created.'''

        self._component_destroy: Set[ComponentId]     = set()
        '''Set of components to be destroyed.'''

        # TODO: Pools instead of allowing stuff to be allocated/deallocated?
        self._component_by_id:   Dict[ComponentId, Component]           = {}
        '''Existing Components indexed by ID.'''

        self._component_by_type: Dict[Type[Component], List[Component]] = {}
        '''Existing Components indexed by Type (a list for each type).'''

        # TODO [2020-10-02]: Remove this or no?
        self._config:            Configuration        = None
        '''The Configuration.'''

    def __init__(self,
                 config:        Optional[Configuration],
                 event_manager: Optional[EventManager],
                 debug_flags:   NullNoneOr[DebugFlag]) -> None:
        '''Initializes this thing.'''
        super().__init__(event_manager, debug_flags)

        self._config = config

    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------

    @classmethod
    def dotted(klass: 'ComponentManager') -> str:
        '''
        The dotted name this Manager has.
        '''
        return 'veredi.game.ecs.manager.component'

    def get_background(self):
        '''
        Data for the Veredi Background context.
        '''
        return {
            background.Name.DOTTED.key: self.dotted(),
        }

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------

    def _cycle_apocalypse(self) -> VerediHealth:
        '''
        Game is ending gracefully. Make sure to murder everyone.
        '''
        # Mark every component for destruction, then run destruction.
        for cid in self._component_by_id:
            self.destroy(cid)
        health = self.destruction(None)

        health = health.update(
            super()._cycle_apocalypse())

        self.health = health
        return health

    def _add(self, id: ComponentId, component: Component) -> None:
        '''
        Insert this component into our pools.
        '''
        self._component_by_id[id] = component
        type_dict = self._component_by_type.setdefault(type(component), [])
        type_dict.append(component)

    def _remove(self, id: ComponentId) -> None:
        '''
        Take this component out of our pools.
        '''
        component = self._component_by_id.pop(id, None)
        if not component:
            return

        type_list = self._component_by_type.setdefault(type(component), [])
        try:
            type_list.remove(component)
        except ValueError:
            # Don't care if it's already not there.
            pass

    # -------------------------------------------------------------------------
    # API: Component Collection Iteration
    # -------------------------------------------------------------------------

    def each_of_type(self, comp_type: Type[Component]) -> Iterable[Component]:
        '''
        Returns a generator that will return each component of the
        required type.
        '''
        # Look for the specific type, and all parent types.
        for type in comp_type.__class__.__mro__:
            # Walk over all components in that type list...
            for component in self._component_by_type[type]:
                yield component

    # -------------------------------------------------------------------------
    # API: Component/Component Management
    # -------------------------------------------------------------------------

    def get(self, component_id: ComponentId) -> CompOrNull:
        '''
        USES Null PATTERN!!!

        Get component from the component pool and return it. Component's
        LifeCycle is not checked so it might not be alive yet/anymore.

        Returns the Component object or the Null() singleton object.
        '''
        return self._component_by_id.get(component_id, Null())

    def get_with_log(self,
                     caller: str,
                     entity_id: 'EntityId',
                     comp_type: Type['Component'],
                     event:     NullNoneOr['Event']         = None,
                     context:   NullNoneOr['VerediContext'] = None,
                     preface:   Optional[str]               = None
                     ) -> Nullable['Component']:
        '''
        Checks to see if entity exists and has a component of the correct type.

        Returns the entity's component if so.
        Logs at INFO level and returns Null if not.

        Automatically creates preface for events: 'Dropping event {event} - '
        But if `preface` is not None, it will use that. So for commands, e.g.:
          'Dropping command {command_name} - '
        could be a good preface. Note the trailing space.

        Prepends `caller` to log.
          f'{self.__class__.__name__}.<insert_method_name_here>'
        Is a decent string to pass.
        '''
        # entity or Null(), so... No need to check.
        entity = background.manager.entity.get_with_log(caller,
                                                        entity_id,
                                                        event=event,
                                                        context=context,
                                                        preface=preface)

        # Now we can (try to) get the component, with logging if None/Null.
        component = entity.get(comp_type)
        if not component:
            preface = preface or ''
            if event:
                preface = preface or f"Dropping event {event} - "
                if not context:
                    context = event.context
            # Component disappeared, and that's ok.
            self._log_info("{}: {}No '{}' on entity: {}",
                           caller,
                           preface,
                           component.__class__.__name__,
                           entity,
                           context=context)
            # TODO [2020-06-04]: a health thing? e.g.
            # self._health_update(ComponentDNE)
            return Null()

        return component

    def _create_by_registry(self,
                            cid: ComponentId,
                            dotted_str: str,
                            context: Optional[VerediContext],
                            *args: Any,
                            **kwargs: Any) -> CompOrNull:
        '''
        Checks the registry for the Component by string and tries
        to create it.

        Returns the component created or None if it cannot create
        the component.

        Raises VerediError or subclasses.
        '''
        component = None
        try:
            component = self._config.create_from_label(dotted_str,
                                                       cid,
                                                       *args,
                                                       context=context,
                                                       **kwargs)
        except Exception as error:
            raise self._log_exception(
                EcsComponentError,
                "Exception during Component creation for would-be "
                "component_id {}. dotted_str: {}, args: {}, "
                "kwargs: {}, context: {}",
                cid, dotted_str, args, kwargs, context
            ) from error

        return component

    def _create_by_type(self,
                        cid: ComponentId,
                        comp_class: Type[Component],
                        context: Optional[VerediContext],
                        *args: Any,
                        **kwargs: Any) -> CompOrNull:
        '''
        Creates a component of type `comp_class` with the supplied args.

        Returns the component created or None if it cannot create
        the component.

        Raises VerediError or subclasses.
        '''
        component = None
        try:
            component = comp_class(context, cid, *args, **kwargs)
        except Exception as error:
            raise self._log_exception(
                EcsComponentError,
                "Exception during Component creation for would-be "
                "component_id {}. comp_class: {}, context: {}",
                cid, comp_class, context
            ) from error

        return component

    def create(self,
               dotted_str_or_type: Union[str, Type[Component]],
               context: Optional[VerediContext],
               *args: Any,
               **kwargs: Any) -> ComponentId:
        '''
        Creates a component with the supplied args. This is the start of
        the life cycle of the component.

        Returns the component id or ComponentId.INVALID it cannot
        create the component.

        Component will be cycled to ALIVE during the CREATION tick.
        '''
        cid = self._component_id.next()

        # Choose what kind of creating we're doing.
        component = None
        by_type = False
        try:
            by_type = Component in dotted_str_or_type.mro()
        except AttributeError:
            by_type = False

        if by_type:
            component = self._create_by_type(cid, dotted_str_or_type,
                                             context, *args, **kwargs)
        else:
            component = self._create_by_registry(cid, dotted_str_or_type,
                                                 context, *args, **kwargs)

        # Die if we created nothing.
        if not component:
            raise self._log_exception(
                EcsComponentError,
                "Failed to create Component for would-be "
                "component_id {}. got: {}, str_or_type: {}, args: {}, "
                "kwargs: {}, context: {}",
                cid, component, dotted_str_or_type, args, kwargs, context
            )

        # Finish adding since we created something.
        self._add(cid, component)
        self._component_create.add(cid)
        component._life_cycled(ComponentLifeCycle.CREATING)

        # And fire off an event for CREATING.
        self._event_create(ComponentLifeEvent,
                           cid,
                           ComponentLifeCycle.CREATING,
                           None, False)

        return cid

    def destroy(self, component_id: ComponentId) -> None:
        '''
        Cycles component to DESTROYING now... This is the 'end' of the life
        cycle of the component.

        Component will be fully removed from our pools on the DESTRUCTION tick.
        '''
        component = self.get(component_id)
        if not component:
            return

        component._life_cycle = ComponentLifeCycle.DESTROYING
        self._component_destroy.add(component.id)

        # And fire off an event for DESTROYING.
        self._event_create(ComponentLifeEvent,
                           component_id,
                           ComponentLifeCycle.DESTROYING,
                           None, False)

    # -------------------------------------------------------------------------
    # Game Loop: Component Life Cycle Updates
    # -------------------------------------------------------------------------

    def creation(self,
                 time: 'TimeManager') -> VerediHealth:
        '''
        Runs before the start of the tick/update loop.

        Updates components in CREATING state to ALIVE state.
        '''

        for component_id in self._component_create:
            # Component should exist in our pool, otherwise we don't
            # care about it...
            component = self.get(component_id)
            if (not component
                    or component._life_cycle != ComponentLifeCycle.CREATING):
                continue

            try:
                # Bump it to alive now.
                component._life_cycled(ComponentLifeCycle.ALIVE)

            except EcsComponentError as error:
                self._log_exception(
                    error,
                    "EcsComponentError in creation() for component_id {}.",
                    component_id)
                # TODO: put this component in... jail or something? Delete?

            # And fire off an event for ALIVE.
            self._event_create(ComponentLifeEvent,
                               component_id,
                               ComponentLifeCycle.ALIVE,
                               None, False)

        # Done with iteration - clear the adds.
        self._component_create.clear()

        return VerediHealth.HEALTHY

    def destruction(self,
                    time: 'TimeManager') -> VerediHealth:
        '''
        Runs after the end of the tick/update loop.

        Removes components not in ALIVE state from component pools.
        '''
        # Check all components in the destroy pool...
        for component_id in self._component_destroy:
            # Component should exist in our pool, otherwise we don't
            # care about it...
            component = self.get(component_id)
            if (not component
                    # INVALID, CREATING, DESTROYING will all be
                    # cycled into death. ALIVE can stay.
                    or component._life_cycle == ComponentLifeCycle.ALIVE):
                continue

            try:
                # Bump it to dead now.
                component._life_cycled(ComponentLifeCycle.DEAD)
                self._remove(component_id)

            except EcsComponentError as error:
                self._log_exception(
                    error,
                    "EcsComponentError in destruction() for component_id {}.",
                    component_id)
                # TODO: put this component in... jail or something?
                # Delete harder?

            # And fire off an event for DEAD.
            self._event_create(ComponentLifeEvent,
                               component_id,
                               ComponentLifeCycle.DEAD,
                               None, False)

        # Done with iteration - clear the removes.
        self._component_destroy.clear()

        return VerediHealth.HEALTHY
