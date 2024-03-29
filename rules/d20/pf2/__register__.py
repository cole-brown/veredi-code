# coding: utf-8

'''
Module for auto-magical registration shenanigans.

This will be found and imported by run.registry in order to have whatever
Registries, Registrars, and Registrees this provides available at run-time.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from veredi.data.registration import config, codec


# -----------------------------------------------------------------------------
# Imports: Registration
# -----------------------------------------------------------------------------

from .game import PF2RulesGame
from . import ability
from . import skill
from . import health
from . import combat


# -----------------------------------------------------------------------------
# Registration
# -----------------------------------------------------------------------------

config.register(PF2RulesGame)

config.register(ability.component.AbilityComponent)
config.register(ability.system.AbilitySystem)

config.register(skill.component.SkillComponent)
config.register(skill.system.SkillSystem)

codec.register_enum(health.component.HealthState,
                    dotted='veredi.rules.d20.pf2.health.state',
                    name_encode='health.state',
                    enum_encode_type=codec.enum.EnumEncodeName)

config.register(health.component.HealthComponent)

config.register(combat.component.AttackComponent)
config.register(combat.component.DefenseComponent)
config.register(combat.system.CombatSystem)


# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = [
    # No exports? Just a registration thing.
]
