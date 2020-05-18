# coding: utf-8

'''
An entity is just a grab bag of Components with an EntityId associated to it.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import (Optional, Iterable, Set, Any, NewType,
                    Dict, Union, Type, Callable)
import enum

from veredi.logger import log
from .identity import (ComponentId,
                       EntityId)
from .component import (Component,
                        CompIdOrType)


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

EntityTypeId = NewType('EntityTypeId', int)
INVALID_ENTITY_TYPE_ID = EntityTypeId(0)

@enum.unique
class EntityLifeCycle(enum.Enum):
    INVALID    = 0
    CREATING   = enum.auto()
    ALIVE      = enum.auto()
    DESTROYING = enum.auto()
    DEAD       = enum.auto()

    def __str__(self):
        return (
            f"{self.__class__.__name__}.{self._name_}"
        )

    def __repr__(self):
        return (
            f"ELC.{self._name_}"
        )


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

class class_property_readonly(object):
    '''
    Decorator for defining a function as a class-level property.
    '''
    def __init__(self, f):
        self.f = f
    def __get__(self, obj, owner):
        return self.f(owner)


class EntityTools:
    '''
    Singleton instance to hold pointers back to EntityManager, ComponentManager.
    '''
    # --------------------------------------------------------------------------
    # Singleton
    # --------------------------------------------------------------------------
    __singleton = None

    def __new__(klass, *args):
        '''
        Enforce the singleness of the singleton.
        '''
        if klass.__singleton is None:
            klass.__singleton = object.__new__(klass)
        # klass.__singleton.val = val
        return klass.__singleton

    @class_property_readonly
    def singleton(klass):
        return klass.__singleton

    # --------------------------------------------------------------------------
    # Constructor
    # --------------------------------------------------------------------------
    def __init__(self,
                 entity_mgr:    'EntityManager',
                 component_mgr: 'ComponentManager'):
        self._entity_manager    = entity_mgr
        self._component_manager = component_mgr

    # --------------------------------------------------------------------------
    # Accessors for the two managers.
    # --------------------------------------------------------------------------

    @class_property_readonly
    def entity_manager(klass):
        return klass.__singleton._entity_manager

    @class_property_readonly
    def component_manager(klass):
        return klass.__singleton._component_manager


class Entity:
    '''
    An Entity tracks its EntityId and life cycle, but primarily holds a
    collection of its Components. The components /are/ the entity,
    basically.
    '''

    __get_component_fn : Optional[Callable[[ComponentId], Optional[Component]]] = None

    @classmethod
    def set_comp_getter(klass: 'Entity',
                        getter: Optional[Callable[[ComponentId], Optional[Component]]]):
        klass.__get_component_fn = getter

    def __init__(self,
                 eid:      EntityId,
                 tid:      EntityTypeId,
                 tools:    EntityTools,
                 *args:    Any,
                 **kwargs: Any) -> None:
        '''DO NOT CALL THIS UNLESS YOUR NAME IS EntityManager!'''
        self._entity_id:  EntityId        = eid
        self._type_id:    EntityTypeId    = tid
        self._life_cycle: EntityLifeCycle = EntityLifeCycle.INVALID
        self._tools:      EntityTools     = tools

        # TODO:
        #  - only hold on to component ids.
        #  - have getters go ask ComponentManager for component?
        self._components : Dict[Type[Component], Component] = {}
        for arg in args:
            if isinstance(arg, Iterable):
                for each in arg:
                    if isinstance(each, (ComponentId, Component)):
                        self._add(each)
            elif isinstance(arg, (ComponentId, Component)):
                self._add(arg)
            # else:
            #     # No other use for arg right now...

        # No use for kwargs right now...

    @property
    def id(self) -> EntityId:
        return self._entity_id

    @property
    def type_id(self) -> EntityTypeId:
        return self._type_id

    @property
    def enabled(self) -> bool:
        return self._life_cycle == EntityLifeCycle.ALIVE

    @property
    def life_cycle(self) -> EntityLifeCycle:
        return self._life_cycle

    def _life_cycled(self, new_state: EntityLifeCycle) -> None:
        '''
        EntityManager calls this to update life cycle. Will be called on:
          - INVALID  -> CREATING   : During EntityManager.create().
          - CREATING -> ALIVE      : During EntityManager.creation()
          - ALIVE    -> DESTROYING : During EntityManager.destroy().
          - DESTROYING -> DEAD     : During EntityManager.destruction()
        '''
        self._life_cycle = new_state

    def get(self, id_or_type: CompIdOrType) -> Optional[Component]:
        '''
        Gets a component from this entity by ComponentId or ComponentType. Will
        return the component instance or None.
        '''
        # Try to get by type first...
        component = self._components.get(id_or_type, None)
        if component:
            return component

        # Ok... id maybe?
        if self.__get_component_fn:
            component = self.__get_component_fn(id_or_type)
            if component:
                # Make sure it's ours...
                my_comp = self._components.get(type(component), None)
                if my_comp and component == my_comp:
                    return component

        # Fall thorough - ain't got that one.
        return None

    def contains(self,
                 comp_set: Set[CompIdOrType]) -> bool:
        '''
        Returns true if this entity is a superset of the desired components.
        I.e. if entity owns all these required ComponentIds/ComponentTypes.
        '''
        # For each component, check that it's in our dictionary.
        return all(self.__contains__(component)
                   for component in comp_set)

    # -------------------------------------------------------------------------
    # EntityManager Interface/Helpers
    # -------------------------------------------------------------------------

    def _add(self, id_or_comp: Union[ComponentId, Component]):
        '''
        DO NOT CALL THIS UNLESS YOUR NAME IS EntityManager!

        Adds the component to this entity.
        '''
        component = id_or_comp
        if isinstance(id_or_comp, ComponentId):
            component = self._tools.component_manager.get(id_or_comp)
        if not component:
            log.error("Ignoring 'add' requested for a non-existing component. "
                      "ID or instance: {} -> {}",
                      id_or_comp, component)
            return

        existing = self._components.get(type(component), None)
        if not existing:
            self._components[type(component)] = component
        else:
            # Entity has component already and it cannot
            # be replaced.
            log.warning(
                "Ignoring 'add' requested for component type already existing "
                "on entity. entity_id: {}, existing: {}, requested: {}",
                self.id, existing, component)

    def _add_all(self, components: Iterable[Component]) -> None:
        '''
        DO NOT CALL THIS UNLESS YOUR NAME IS EntityManager!

        Tries to add() all the supplied components to this entity.
        '''
        for each in components:
            self._add(each)

    def _remove(self, id_or_type: CompIdOrType) -> Optional[Component]:
        '''
        DO NOT CALL THIS UNLESS YOUR NAME IS EntityManager!

        Removes a component from the entity.
        Returns component if found & removed, else None.
        '''
        # Type passed in?
        component = self._components.pop(id_or_type, None)
        if component:
            return component

        # Ok... id maybe?
        if self.__get_component_fn:
            component = self.__get_component_fn(id_or_type)
            if component:
                # Make sure it's ours...
                my_comp = self._components.get(type(component), None)
                if my_comp and component == my_comp:
                    return component

        return None

    def _remove_all(self, components: Iterable[CompIdOrType]) -> None:
        '''
        DO NOT CALL THIS UNLESS YOUR NAME IS EntityManager!

        Tries to remove() all the supplied components from the entity.
        '''
        for each in components:
            self._remove(each)

    # --------------------------------------------------------------------------
    # Python Interfaces (hashable, ==, 'in')
    # --------------------------------------------------------------------------

    # def __hash__(self):
    #     '''
    #     __hash__ and __eq__ needed for putting in dict, set. We'll make it a
    #     bit easier since EntityId must be unique.
    #     '''
    #     return hash(self._entity_id)

    def __eq__(self, other: Any):
        '''
        Entity == Entity is just an id equality check. Otherwise uses id() func.
        '''
        if isinstance(other, Entity):
            return self.id == other.id

        return id(self) == id(other)

    def __contains__(self, key: CompIdOrType):
        '''
        This is for any "if component in entity:" sort of check systems
        might want to do.
        '''
        # Don't eval all them args unless it'll be used...
        if log.will_output(log.Level.DEBUG):
            log.debug("{} contains {}? {} -> {}\n    all: {}",
                      self.__class__.__name__,
                      key,
                      self.get(key),
                      bool(self.get(key)),
                      self._components)
        return bool(self.get(key))

    def __str__(self):
        ent_str = (
            f"{self.__class__.__name__}"
            f"[id:{self.id:03d}, "
            f"type:{self.type_id:03d}, "
            f"{str(self.life_cycle)}]: "
        )
        comps = []
        for each in self._components.values():
            comps.append(str(each))
        comp_str = ', '.join(comps)
        return ent_str + '{' + comp_str + '}'

    def __repr__(self):
        ent_str = (
            f"{self.__class__.__name__}"
            f"[id:{self.id:03d}, "
            f"type:{self.type_id:03d}, "
            f"{repr(self.life_cycle)}]: "
        )
        comps = []
        for each in self._components.values():
            comps.append(repr(each))
        comp_str = ', '.join(comps)
        return '<v.ent:' + ent_str + '{' + comp_str + '}>'
